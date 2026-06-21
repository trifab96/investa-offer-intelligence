"""Enrichment orchestrator: runs all external sources with DB caching."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.enrichment import mietspiegel, nominatim, overpass, wikidata
from app.pipeline.enrichment.cache import get_cached, store_cache
from app.schemas.models import EnrichmentBundle, Extraction, GeoResult

logger = logging.getLogger(__name__)


async def geocode_offer(extraction: Extraction) -> GeoResult | None:
    """Geocode early (needed by dedup before an object_id exists)."""
    return await nominatim.geocode(extraction)


async def enrich(
    session: AsyncSession,
    object_id: uuid.UUID,
    extraction: Extraction,
    geo: GeoResult | None,
) -> EnrichmentBundle:
    """Build the enrichment bundle, using the per-object cache where possible."""
    sources: list[str] = []
    bundle = EnrichmentBundle(geo=geo)

    if geo:
        bundle.sources.append("nominatim")
        sources.append("nominatim")
        await store_cache(session, object_id, "nominatim", geo.model_dump())

    # POIs (Overpass) — only if geocoded.
    if geo and geo.lat is not None:
        poi = await get_cached(session, object_id, "overpass")
        if poi is None:
            poi = await overpass.fetch_pois(geo.lat, geo.lon)
            await store_cache(session, object_id, "overpass", poi)
        bundle.poi = poi
        bundle.sources.append("overpass")

    # Demographics (Wikidata).
    ort = extraction.lage.ort or (geo.ort if geo else None)
    if ort:
        demo = await get_cached(session, object_id, "wikidata")
        if demo is None:
            demo = await wikidata.fetch_demographics(ort)
            await store_cache(session, object_id, "wikidata", demo)
        bundle.demographics = demo
        bundle.sources.append("wikidata")

    # Rent / price benchmark (seed dataset; cheap, still cached for traceability).
    plz = extraction.lage.plz or (geo.plz if geo else None)
    rent = mietspiegel.lookup(plz, ort)
    await store_cache(session, object_id, "mietspiegel_seed", rent)
    bundle.rent_benchmark = rent
    bundle.sources.append("mietspiegel_seed")

    return bundle
