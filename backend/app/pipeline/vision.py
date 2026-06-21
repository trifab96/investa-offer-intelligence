"""Image analysis (4.4c, optional): render PDF pages / images and run a vision LLM.

The teasers are visually rich (site plans, floor plans, renderings). This module
collects a small set of images from the uploaded files, sends them to the vision
model, and returns a structured :class:`VisionAnalysis` plus a prompt trace. It
complements — never replaces — the text extraction.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from app.config import get_settings
from app.llm.client import get_llm
from app.llm.prompts import load_prompt, render
from app.schemas.models import VisionAnalysis

if TYPE_CHECKING:
    from app.pipeline.ingestion import ParsedDocument

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_EDGE = 1100  # downscale long edge to bound payload size


async def analyze_images(
    subject: str | None, documents: list["ParsedDocument"]
) -> tuple[VisionAnalysis | None, dict[str, Any] | None]:
    """Collect images from parsed documents and run the vision model.

    Works for both directly uploaded PDFs/images (read from disk) and
    attachments embedded in a .msg/.eml (rendered from in-memory bytes).
    """
    if not settings.vision_enabled:
        return None, None

    images = _collect_images(documents, settings.vision_max_images)
    if not images:
        return None, None

    system = load_prompt("vision_system")
    user = render("vision_user", subject=subject or "Angebot")
    parsed, trace = await get_llm().complete_vision_json(
        system=system, user=user, images=images, purpose="image_analysis"
    )
    try:
        analysis = VisionAnalysis.model_validate(parsed)
    except ValidationError as exc:
        logger.warning("Vision validation failed: %s", exc)
        analysis = VisionAnalysis(confidence=0.0)
    analysis.images_analyzed = len(images)
    return analysis, trace


# --------------------------------------------------------------------------- #
# Image collection / rendering
# --------------------------------------------------------------------------- #
def _collect_images(documents: list["ParsedDocument"], limit: int) -> list[str]:
    """Return up to ``limit`` base64 PNG data URLs from PDF/image documents."""
    out: list[str] = []
    for doc in documents:
        if len(out) >= limit:
            break
        data = _doc_bytes(doc)
        if data is None:
            continue
        if doc.doc_type == "image":
            url = _image_bytes_to_data_url(data)
            if url:
                out.append(url)
        elif doc.doc_type == "pdf":
            out.extend(_pdf_bytes_to_data_urls(data, limit - len(out)))
    return out[:limit]


def _doc_bytes(doc: "ParsedDocument") -> bytes | None:
    """Get a document's raw bytes from memory (attachments) or disk (uploads)."""
    if doc.raw_bytes:
        return doc.raw_bytes
    if doc.storage_path:
        try:
            return Path(doc.storage_path).read_bytes()
        except OSError:
            return None
    return None


def render_document_pages(doc: "ParsedDocument", limit: int) -> list[str]:
    """Render a single document (PDF pages / image) to PNG data URLs for preview."""
    if limit <= 0:
        return []
    data = _doc_bytes(doc)
    if data is None:
        return []
    if doc.doc_type == "pdf":
        return _pdf_bytes_to_data_urls(data, limit)
    if doc.doc_type == "image":
        url = _image_bytes_to_data_url(data)
        return [url] if url else []
    return []



def _pdf_bytes_to_data_urls(data: bytes, limit: int) -> list[str]:
    """Render the first ``limit`` PDF pages to PNG data URLs via pypdfium2."""
    if limit <= 0:
        return []
    try:
        import pypdfium2 as pdfium
    except ImportError:  # pragma: no cover
        logger.info("pypdfium2 not available; skipping PDF image rendering")
        return []

    urls: list[str] = []
    try:
        pdf = pdfium.PdfDocument(data)
        n = min(len(pdf), limit)
        for i in range(n):
            bitmap = pdf[i].render(scale=1.4)
            url = _pil_to_data_url(bitmap.to_pil())
            if url:
                urls.append(url)
        pdf.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF render failed: %s", exc)
    return urls


def _image_bytes_to_data_url(data: bytes) -> str | None:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as img:
            return _pil_to_data_url(img.convert("RGB"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image load failed: %s", exc)
        return None


def _pil_to_data_url(img: Any) -> str | None:
    """Downscale and encode a PIL image as a base64 PNG data URL."""
    try:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        scale = min(1.0, _MAX_EDGE / max(w, h))
        if scale < 1.0:
            img = img.resize((int(w * scale), int(h * scale)))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image encode failed: %s", exc)
        return None

