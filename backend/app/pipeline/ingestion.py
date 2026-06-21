"""Ingestion (4.1): parse uploaded email + attachments into text.

Supports Outlook ``.msg``, RFC822 ``.eml``, PDF (text layer with OCR fallback),
plain text and images. Returns a list of parsed documents plus a combined
corpus that downstream extraction consumes.
"""

from __future__ import annotations

import email
import logging
import re
from dataclasses import dataclass, field
from email import policy
from pathlib import Path

logger = logging.getLogger(__name__)

# Control chars that PostgreSQL TEXT columns reject (NUL) or that add noise.
# Keep tab/newline/carriage-return; strip the rest of the C0 range + NUL.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(text: str | None) -> str:
    """Remove NUL/control bytes so extracted text is safe to store in Postgres."""
    if not text:
        return ""
    return _CONTROL_CHARS.sub("", text)


@dataclass
class ParsedDocument:
    filename: str
    doc_type: str
    text: str
    storage_path: str | None = None
    # Raw bytes for binary docs (e.g. PDF/image attachments parsed from a .msg),
    # kept in-memory so downstream image analysis can render them. Not persisted.
    raw_bytes: bytes | None = None

    def __post_init__(self) -> None:
        # Guarantee DB-safe text regardless of the parser that produced it.
        self.text = sanitize_text(self.text)


@dataclass
class IngestResult:
    subject: str | None = None
    sender: str | None = None
    body_text: str | None = None
    documents: list[ParsedDocument] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        parts: list[str] = []
        if self.subject:
            parts.append(f"BETREFF: {self.subject}")
        if self.sender:
            parts.append(f"ABSENDER: {self.sender}")
        for doc in self.documents:
            if doc.text and doc.text.strip():
                parts.append(f"\n--- {doc.filename} ({doc.doc_type}) ---\n{doc.text}")
        return "\n".join(parts).strip()


# --------------------------------------------------------------------------- #
# File-type dispatch
# --------------------------------------------------------------------------- #
def ingest_path(path: Path) -> IngestResult:
    """Ingest a single uploaded file by extension, with content sniffing fallback."""
    suffix = path.suffix.lower()
    if suffix == ".msg":
        return _ingest_msg(path)
    if suffix == ".eml":
        return _ingest_eml(path)
    if suffix == ".pdf":
        text = _pdf_to_text(path)
        return IngestResult(
            subject=path.stem,
            documents=[ParsedDocument(path.name, "pdf", text, str(path))],
        )
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}:
        text = _image_to_text(path)
        return IngestResult(
            subject=path.stem,
            documents=[ParsedDocument(path.name, "image", text, str(path))],
        )

    # Unknown / missing extension (e.g. MIME-encoded upload filenames): fall back
    # to content sniffing so we never misread a binary PDF/image as text.
    sniffed = _sniff_type(path)
    if sniffed == "pdf":
        text = _pdf_to_text(path)
        return IngestResult(
            subject=path.stem,
            documents=[ParsedDocument(path.name, "pdf", text, str(path))],
        )
    if sniffed == "image":
        text = _image_to_text(path)
        return IngestResult(
            subject=path.stem,
            documents=[ParsedDocument(path.name, "image", text, str(path))],
        )

    # Final fallback: treat as text.
    text = path.read_text(encoding="utf-8", errors="ignore")
    return IngestResult(
        subject=path.stem,
        documents=[ParsedDocument(path.name, "text", text, str(path))],
    )


def _sniff_type(path: Path) -> str | None:
    """Detect common file types by magic bytes when the extension is unreliable."""
    try:
        with path.open("rb") as fh:
            head = fh.read(8)
    except OSError:
        return None
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\x89PNG") or head[:3] == b"\xff\xd8\xff" or head[:4] in (
        b"II*\x00",
        b"MM\x00*",
    ):
        return "image"
    return None


def merge_results(results: list[IngestResult]) -> IngestResult:
    """Merge multiple uploaded files into one offer-level ingest result."""
    merged = IngestResult()
    for r in results:
        merged.subject = merged.subject or r.subject
        merged.sender = merged.sender or r.sender
        if r.body_text:
            merged.body_text = (merged.body_text or "") + "\n" + r.body_text
        merged.documents.extend(r.documents)
    return merged


# --------------------------------------------------------------------------- #
# Email parsers
# --------------------------------------------------------------------------- #
def _ingest_msg(path: Path) -> IngestResult:
    """Parse an Outlook .msg, including its attachments."""
    try:
        import extract_msg
    except ImportError:  # pragma: no cover
        logger.warning("extract-msg not installed; cannot parse %s", path.name)
        return IngestResult(subject=path.stem)

    msg = extract_msg.Message(str(path))
    docs: list[ParsedDocument] = []
    body = msg.body or ""
    docs.append(ParsedDocument(f"{path.stem}.body", "email_body", body))

    for att in msg.attachments:
        fname = att.longFilename or att.shortFilename or "attachment"
        data = att.data
        if not isinstance(data, (bytes, bytearray)):
            continue
        docs.extend(_parse_attachment_bytes(fname, bytes(data)))

    return IngestResult(
        subject=msg.subject or path.stem,
        sender=msg.sender,
        body_text=body,
        documents=docs,
    )


def _ingest_eml(path: Path) -> IngestResult:
    """Parse an RFC822 .eml, including attachments."""
    with path.open("rb") as fh:
        msg = email.message_from_binary_file(fh, policy=policy.default)

    docs: list[ParsedDocument] = []
    body_text = ""
    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = part.get_content_disposition()
        if content_type == "text/plain" and disposition != "attachment":
            body_text += part.get_content()
        elif disposition == "attachment":
            fname = part.get_filename() or "attachment"
            payload = part.get_payload(decode=True) or b""
            docs.extend(_parse_attachment_bytes(fname, payload))

    docs.insert(0, ParsedDocument(f"{path.stem}.body", "email_body", body_text))
    return IngestResult(
        subject=msg.get("subject", path.stem),
        sender=msg.get("from"),
        body_text=body_text,
        documents=docs,
    )


def _parse_attachment_bytes(filename: str, data: bytes) -> list[ParsedDocument]:
    """Parse an in-memory attachment by extension into ParsedDocuments."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" or data[:4] == b"%PDF":
        return [ParsedDocument(filename, "pdf", _pdf_bytes_to_text(data), raw_bytes=data)]
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"} or data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG":
        return [
            ParsedDocument(filename, "image", _image_bytes_to_text(data), raw_bytes=data)
        ]
    if suffix in {".txt", ".htm", ".html"}:
        return [ParsedDocument(filename, "text", data.decode("utf-8", "ignore"))]
    # Unknown attachment types are recorded but not text-extracted.
    return [ParsedDocument(filename, "binary", "")]


# --------------------------------------------------------------------------- #
# PDF / image text extraction
# --------------------------------------------------------------------------- #
def _pdf_to_text(path: Path) -> str:
    return _pdf_bytes_to_text(path.read_bytes())


def _pdf_bytes_to_text(data: bytes) -> str:
    """Extract a PDF text layer; fall back to OCR for scanned PDFs."""
    text = ""
    try:
        import io

        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n".join(pages).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed, trying pypdf: %s", exc)
        text = _pdf_pypdf_fallback(data)

    if len(text) < 40:  # likely scanned -> OCR fallback
        ocr = _pdf_ocr_fallback(data)
        if len(ocr) > len(text):
            text = ocr
    return text


def _pdf_pypdf_fallback(data: bytes) -> str:
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("pypdf fallback failed: %s", exc)
        return ""


def _pdf_ocr_fallback(data: bytes) -> str:
    """OCR a (scanned) PDF rendered to images. Best-effort; optional deps."""
    try:
        import io

        import pdfplumber
        import pytesseract

        out: list[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                pil = page.to_image(resolution=200).original
                out.append(pytesseract.image_to_string(pil, lang="deu"))
        return "\n".join(out).strip()
    except Exception as exc:  # noqa: BLE001
        logger.info("OCR fallback unavailable/failed: %s", exc)
        return ""


def _image_to_text(path: Path) -> str:
    return _image_bytes_to_text(path.read_bytes())


def _image_bytes_to_text(data: bytes) -> str:
    """OCR an image to text (optional; returns '' if deps missing)."""
    try:
        import io

        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img, lang="deu").strip()
    except Exception as exc:  # noqa: BLE001
        logger.info("Image OCR unavailable/failed: %s", exc)
        return ""
