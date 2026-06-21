"""REST API routes (FastAPI)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db.models import Analysis, KnownObject, Offer
from app.db.session import get_session
from app.pipeline.orchestrator import process_offer
from app.schemas.models import (
    DocumentOut,
    OfferDetail,
    OfferSummary,
    PortfolioStats,
    PreviewOut,
    PreviewPage,
    ReplyOut,
    StatusOut,
)

router = APIRouter(prefix="/api", tags=["offers"])
settings = get_settings()

# Cap how much document text we ship to the client preview.
_PREVIEW_TEXT_LIMIT = 20_000


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/offers", status_code=202)
async def create_offer(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Upload an email + attachments; returns offer_id and starts the pipeline."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    offer = Offer(id=uuid.uuid4(), status="received")
    session.add(offer)
    await session.commit()

    upload_root = Path(settings.upload_dir) / str(offer.id)
    upload_root.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for f in files:
        filename = _decode_filename(f.filename) or "upload.bin"
        dest = upload_root / Path(filename).name
        dest.write_bytes(await f.read())
        saved_paths.append(str(dest))

    background.add_task(process_offer, offer.id, saved_paths)
    return {"offer_id": str(offer.id), "status": "received"}


def _decode_filename(filename: str | None) -> str | None:
    """Decode RFC 2047 MIME encoded-word filenames (e.g. from non-ASCII names)."""
    if not filename:
        return filename
    if "=?" in filename and "?=" in filename:
        try:
            from email.header import decode_header

            parts = decode_header(filename)
            decoded = "".join(
                (b.decode(enc or "utf-8", "ignore") if isinstance(b, bytes) else b)
                for b, enc in parts
            )
            return decoded or filename
        except Exception:  # noqa: BLE001 — fall back to the raw name
            return filename
    return filename


@router.get("/offers", response_model=list[OfferSummary])
async def list_offers(
    session: AsyncSession = Depends(get_session),
) -> list[OfferSummary]:
    rows = (
        await session.execute(
            select(Offer)
            .options(
                selectinload(Offer.analysis),
                selectinload(Offer.matched_object),
            )
            .order_by(Offer.created_at.desc())
        )
    ).scalars().all()

    out: list[OfferSummary] = []
    for o in rows:
        extraction = (o.analysis.extraction if o.analysis else None) or {}
        out.append(
            OfferSummary(
                id=o.id,
                subject=o.subject,
                sender=o.sender,
                status=o.status,
                score=float(o.analysis.score) if o.analysis and o.analysis.score is not None else None,
                band=o.analysis.band if o.analysis else None,
                is_known=o.object_id is not None and _is_known_match(o),
                objektart=extraction.get("objektart"),
                ort=(extraction.get("lage") or {}).get("ort"),
                created_at=o.created_at,
            )
        )
    return out


@router.get("/offers/{offer_id}", response_model=OfferDetail)
async def get_offer(
    offer_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> OfferDetail:
    o = (
        await session.execute(
            select(Offer)
            .where(Offer.id == offer_id)
            .options(
                selectinload(Offer.analysis),
                selectinload(Offer.documents),
                selectinload(Offer.replies),
            )
        )
    ).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Offer not found")

    a = o.analysis
    return OfferDetail(
        id=o.id,
        subject=o.subject,
        sender=o.sender,
        status=o.status,
        error=o.error,
        is_known=_is_known_match(o),
        documents=[
            DocumentOut(
                id=d.id,
                filename=d.filename,
                doc_type=d.doc_type,
                extracted_text=(d.extracted_text or "")[:_PREVIEW_TEXT_LIMIT] or None,
                char_count=len(d.extracted_text or ""),
            )
            for d in o.documents
        ],
        extraction=a.extraction if a else None,
        enrichment=a.enrichment if a else None,
        scoring=a.scoring if a else None,
        score=float(a.score) if a and a.score is not None else None,
        band=a.band if a else None,
        prompt_trace=a.prompt_trace if a else None,
        replies=[ReplyOut.model_validate(r) for r in o.replies],
        created_at=o.created_at,
    )


@router.get("/offers/{offer_id}/status", response_model=StatusOut)
async def get_status(
    offer_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> StatusOut:
    o = await session.get(Offer, offer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return StatusOut(id=o.id, status=o.status, error=o.error)


@router.get("/offers/{offer_id}/preview", response_model=PreviewOut)
async def get_preview(
    offer_id: uuid.UUID,
    max_pages: int = 8,
    session: AsyncSession = Depends(get_session),
) -> PreviewOut:
    """Render the original uploaded documents (PDF pages / images) to thumbnails.

    Re-reads the offer's stored upload files and renders them on demand so the
    user can see the source material behind the analysis (incl. attachments
    embedded in a .msg/.eml).
    """
    o = await session.get(Offer, offer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Offer not found")

    from app.pipeline.ingestion import ingest_path
    from app.pipeline.vision import render_document_pages

    upload_root = Path(settings.upload_dir) / str(offer_id)
    if not upload_root.exists():
        return PreviewOut(pages=[], note="Originaldateien nicht mehr verfügbar.")

    pages: list[PreviewPage] = []
    for fp in sorted(upload_root.iterdir()):
        if len(pages) >= max_pages:
            break
        try:
            ingest = ingest_path(fp)
        except Exception:  # noqa: BLE001
            continue
        for doc in ingest.documents:
            if len(pages) >= max_pages:
                break
            rendered = render_document_pages(doc, max_pages - len(pages))
            for idx, data_url in enumerate(rendered):
                pages.append(
                    PreviewPage(
                        filename=doc.filename,
                        doc_type=doc.doc_type,
                        page=idx + 1,
                        image=data_url,
                    )
                )
    note = None if pages else "Keine bildbasierte Vorschau verfügbar (nur Text)."
    return PreviewOut(pages=pages, note=note)


@router.get("/stats", response_model=PortfolioStats)
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> PortfolioStats:
    """Portfolio-level KPIs across all offers (decision support overview)."""
    rows = (
        await session.execute(
            select(Offer)
            .options(selectinload(Offer.analysis))
            .order_by(Offer.created_at.desc())
        )
    ).scalars().all()

    processing_states = {
        "received", "parsing", "extracting", "matching", "enriching", "scoring",
    }
    stats = PortfolioStats(total=len(rows), band_counts={}, score_histogram=[0] * 10)
    scores: list[float] = []
    summaries: list[OfferSummary] = []
    for o in rows:
        if o.status == "done":
            stats.done += 1
        elif o.status == "failed":
            stats.failed += 1
        elif o.status in processing_states:
            stats.processing += 1
        if _is_known_match(o):
            stats.known_duplicates += 1
        a = o.analysis
        if a and a.score is not None:
            s = float(a.score)
            scores.append(s)
            stats.scored += 1
            bucket = min(9, int(s))
            stats.score_histogram[bucket] += 1
            if a.band:
                stats.band_counts[a.band] = stats.band_counts.get(a.band, 0) + 1
            extraction = a.extraction or {}
            summaries.append(
                OfferSummary(
                    id=o.id,
                    subject=o.subject,
                    sender=o.sender,
                    status=o.status,
                    score=s,
                    band=a.band,
                    is_known=_is_known_match(o),
                    objektart=extraction.get("objektart"),
                    ort=(extraction.get("lage") or {}).get("ort"),
                    created_at=o.created_at,
                )
            )
    if scores:
        stats.avg_score = round(sum(scores) / len(scores), 2)
    stats.top_offers = sorted(
        summaries, key=lambda s: s.score or 0, reverse=True
    )[:5]
    return stats


@router.get("/objects")
async def list_objects(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (
        await session.execute(select(KnownObject).order_by(KnownObject.first_seen.desc()))
    ).scalars().all()
    return [
        {
            "id": str(o.id),
            "address_raw": o.address_raw,
            "plz": o.plz,
            "ort": o.ort,
            "lat": o.lat,
            "lon": o.lon,
            "first_seen": o.first_seen.isoformat() if o.first_seen else None,
        }
        for o in rows
    ]


@router.get("/compare")
async def compare(
    ids: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Comparison payload for 2-4 offers (ids=comma-separated UUIDs)."""
    try:
        id_list = [uuid.UUID(x) for x in ids.split(",") if x.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id list") from exc

    rows = (
        await session.execute(
            select(Offer)
            .where(Offer.id.in_(id_list))
            .options(selectinload(Offer.analysis))
        )
    ).scalars().all()

    out: list[dict] = []
    for o in rows:
        a = o.analysis
        extraction = (a.extraction if a else None) or {}
        scoring = (a.scoring if a else None) or {}
        out.append(
            {
                "id": str(o.id),
                "subject": o.subject,
                "objektart": extraction.get("objektart"),
                "ort": (extraction.get("lage") or {}).get("ort"),
                "score": float(a.score) if a and a.score is not None else None,
                "band": a.band if a else None,
                "subscores": scoring.get("subscores", []),
                "metrics": scoring.get("metrics", {}),
            }
        )
    return out


def _is_known_match(offer: Offer) -> bool:
    """An offer is 'known' if its analysis recorded a positive dedup match."""
    if not offer.analysis or not offer.analysis.scoring:
        return False
    match = offer.analysis.scoring.get("match")
    return bool(match and match.get("is_match"))
