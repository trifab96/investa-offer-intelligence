"""Pipeline orchestrator: wires steps together and persists status transitions.

Runs as a FastAPI background task. Status flow:
received -> parsing -> extracting -> matching -> enriching -> scoring -> done|failed
(For known objects, enriching/scoring are short-circuited and a broker reply is
drafted instead.)
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis, Document, KnownObject, Offer, Reply
from app.db.session import SessionLocal
from app.pipeline import dedup, extraction as extraction_step
from app.pipeline import reply as reply_step
from app.pipeline import scoring as scoring_step
from app.pipeline import vision as vision_step
from app.pipeline.enrichment import service as enrichment_service
from app.pipeline.ingestion import (
    IngestResult,
    ingest_path,
    merge_results,
    sanitize_text,
)

logger = logging.getLogger(__name__)


async def _set_status(
    session: AsyncSession, offer: Offer, status: str, error: str | None = None
) -> None:
    offer.status = status
    if error:
        offer.error = error
    await session.commit()


async def process_offer(offer_id: uuid.UUID, file_paths: list[str]) -> None:
    """Full pipeline for one offer. Opens its own session (background task)."""
    async with SessionLocal() as session:
        offer = await session.get(Offer, offer_id)
        if offer is None:
            logger.error("Offer %s not found", offer_id)
            return
        try:
            await _run(session, offer, file_paths)
        except Exception as exc:  # noqa: BLE001 — persist failure, never crash worker
            logger.exception("Pipeline failed for %s", offer_id)
            # The failing flush leaves the session in a rolled-back state, so
            # reset it before recording the failure status.
            await session.rollback()
            try:
                offer = await session.get(Offer, offer_id)
                if offer is not None:
                    await _set_status(session, offer, "failed", str(exc))
            except Exception:  # noqa: BLE001 — never let the worker crash
                logger.exception("Could not persist failed status for %s", offer_id)


async def _run(session: AsyncSession, offer: Offer, file_paths: list[str]) -> None:
    # 1) Parsing -------------------------------------------------------------
    await _set_status(session, offer, "parsing")
    results: list[IngestResult] = [ingest_path(Path(p)) for p in file_paths]
    ingest = merge_results(results)

    offer.subject = sanitize_text(offer.subject or ingest.subject) or None
    offer.sender = sanitize_text(offer.sender or ingest.sender) or None
    offer.raw_text = sanitize_text(ingest.combined_text)
    for doc in ingest.documents:
        session.add(
            Document(
                id=uuid.uuid4(),
                offer_id=offer.id,
                filename=doc.filename,
                doc_type=doc.doc_type,
                extracted_text=doc.text,
                storage_path=doc.storage_path,
            )
        )
    await session.commit()

    # 2) Extraction ----------------------------------------------------------
    await _set_status(session, offer, "extracting")
    extraction, ex_trace = await extraction_step.extract_offer(ingest.combined_text)
    traces: list[dict] = [ex_trace]

    # 3) Geocode + Matching --------------------------------------------------
    await _set_status(session, offer, "matching")
    geo = await enrichment_service.geocode_offer(extraction)
    match = await dedup.find_match(session, extraction, geo)

    analysis = Analysis(
        id=uuid.uuid4(),
        offer_id=offer.id,
        extraction=extraction.model_dump(),
        llm_model=ex_trace.get("model"),
    )
    session.add(analysis)

    if match.is_match and match.matched_object_id:
        # Known object -> link, draft reply, short-circuit.
        offer.object_id = match.matched_object_id
        analysis.scoring = {"match": match.model_dump(mode="json")}
        body, reply_trace = await reply_step.draft_known_reply(
            offer.subject, extraction, match
        )
        traces.append(reply_trace)
        session.add(
            Reply(
                id=uuid.uuid4(),
                offer_id=offer.id,
                language="de",
                subject=f"AW: {offer.subject or 'Ihr Angebot'}",
                body=body,
                reason="object_already_known",
            )
        )
        analysis.prompt_trace = traces
        await session.commit()
        await _set_status(session, offer, "done")
        return

    # New object -> register, enrich, score.
    obj: KnownObject = await dedup.register_object(session, extraction, geo)
    offer.object_id = obj.id

    # 4) Enrichment ----------------------------------------------------------
    await _set_status(session, offer, "enriching")
    enrichment = await enrichment_service.enrich(session, obj.id, extraction, geo)

    # 4b) Image analysis (optional, 4.4c) — render pages/images + vision LLM.
    vision_analysis, vision_trace = await vision_step.analyze_images(
        offer.subject, ingest.documents
    )
    if vision_analysis is not None:
        enrichment.image_analysis = vision_analysis.model_dump()
        enrichment.sources.append("image_analysis")
        if vision_trace:
            traces.append(vision_trace)
    analysis.enrichment = enrichment.model_dump()

    # 5) Scoring -------------------------------------------------------------
    await _set_status(session, offer, "scoring")
    scoring, metrics, score_trace = await scoring_step.score_offer(
        extraction, enrichment
    )
    traces.append(score_trace)
    scoring_payload = scoring.model_dump()
    scoring_payload["metrics"] = metrics
    scoring_payload["match"] = match.model_dump(mode="json")
    analysis.scoring = scoring_payload
    analysis.score = scoring.score
    analysis.band = scoring.band
    analysis.prompt_trace = traces

    await session.commit()
    await _set_status(session, offer, "done")


async def list_offer_ids(session: AsyncSession) -> list[uuid.UUID]:
    rows = (await session.execute(select(Offer.id))).scalars().all()
    return list(rows)
