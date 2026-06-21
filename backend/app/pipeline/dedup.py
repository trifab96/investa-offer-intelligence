"""Dedup / object recognition (4.2 — mandatory).

Hybrid, explainable matching:
1. normalize the offer address
2. fetch candidate known objects via pg_trgm similarity (fast prefilter)
3. score candidates with RapidFuzz token_sort_ratio + geo Haversine
4. decide match / needs_review / new using configurable thresholds
Match evidence is returned and persisted so every decision is auditable.
"""

from __future__ import annotations

import logging
import uuid

from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import KnownObject
from app.pipeline.addressing import haversine_m, normalize_address
from app.schemas.models import Extraction, GeoResult, MatchEvidence

logger = logging.getLogger(__name__)
settings = get_settings()


async def find_match(
    session: AsyncSession,
    extraction: Extraction,
    geo: GeoResult | None,
) -> MatchEvidence:
    """Return match evidence for the offer against the known-object registry."""
    address_norm = normalize_address(extraction.lage)
    if not address_norm:
        return MatchEvidence(is_match=False, reason="no_address")

    # 1) Trigram prefilter using the similarity() function (avoids the '%'
    #    operator, which clashes with the DBAPI parameter style).
    rows = (
        await session.execute(
            text(
                """
                SELECT id, address_norm, lat, lon,
                       similarity(address_norm, :addr) AS sim
                FROM objects
                WHERE similarity(address_norm, :addr) > 0.2
                ORDER BY sim DESC
                LIMIT 10
                """
            ),
            {"addr": address_norm},
        )
    ).all()

    best: MatchEvidence | None = None
    for row in rows:
        # 2) Refine with RapidFuzz token_sort_ratio (0..1).
        addr_sim = fuzz.token_sort_ratio(address_norm, row.address_norm) / 100.0

        # 3) Geo gate (if both sides geocoded).
        geo_dist: float | None = None
        if geo and geo.lat is not None and row.lat is not None:
            geo_dist = haversine_m(geo.lat, geo.lon, row.lat, row.lon)

        is_match, needs_review, reason = _decide(addr_sim, geo_dist)
        candidate = MatchEvidence(
            is_match=is_match,
            needs_review=needs_review,
            matched_object_id=row.id,
            address_similarity=round(addr_sim, 3),
            geo_distance_m=round(geo_dist, 1) if geo_dist is not None else None,
            reason=reason,
        )
        if best is None or addr_sim > (best.address_similarity or 0):
            best = candidate

    if best and (best.is_match or best.needs_review):
        return best
    return MatchEvidence(is_match=False, reason="no_candidate_over_threshold")


def _decide(addr_sim: float, geo_dist: float | None) -> tuple[bool, bool, str]:
    strong = settings.dedup_address_sim_strong
    weak = settings.dedup_address_sim_weak
    geo_gate = settings.dedup_geo_distance_m

    if addr_sim >= strong:
        return True, False, f"address_similarity {addr_sim:.2f} >= {strong}"
    if addr_sim >= weak and geo_dist is not None and geo_dist <= geo_gate:
        return True, False, (
            f"address_similarity {addr_sim:.2f} >= {weak} and "
            f"geo_distance {geo_dist:.0f}m <= {geo_gate:.0f}m"
        )
    if addr_sim >= weak:
        return False, True, (
            f"ambiguous: address_similarity {addr_sim:.2f} in "
            f"[{weak}, {strong}) without geo confirmation"
        )
    return False, False, f"address_similarity {addr_sim:.2f} < {weak}"


async def register_object(
    session: AsyncSession,
    extraction: Extraction,
    geo: GeoResult | None,
) -> KnownObject:
    """Create and persist a new canonical known object."""
    address_norm = normalize_address(extraction.lage)
    obj = KnownObject(
        id=uuid.uuid4(),
        address_raw=" ".join(
            p
            for p in [
                extraction.lage.strasse,
                extraction.lage.hausnummer,
                extraction.lage.plz,
                extraction.lage.ort,
            ]
            if p
        )
        or extraction.lage.lagebeschreibung,
        address_norm=address_norm or "unknown",
        plz=extraction.lage.plz or (geo.plz if geo else None),
        ort=extraction.lage.ort or (geo.ort if geo else None),
        lat=geo.lat if geo else None,
        lon=geo.lon if geo else None,
        dedup_key=address_norm,
    )
    session.add(obj)
    await session.flush()
    return obj
