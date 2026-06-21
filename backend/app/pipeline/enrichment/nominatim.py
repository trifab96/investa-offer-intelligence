"""Geocoding via Nominatim (OSM). Also resolves incomplete addresses (4.4c)."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.pipeline.enrichment.cache import request_json
from app.schemas.models import Extraction, GeoResult

logger = logging.getLogger(__name__)
settings = get_settings()


async def geocode(extraction: Extraction) -> GeoResult | None:
    """Geocode an offer's location using structured then free-text queries."""
    loc = extraction.lage
    query = _build_query(extraction)
    if not query:
        return None

    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
        "countrycodes": "de",
    }
    url = f"{settings.nominatim_base_url}/search"
    data = await request_json("GET", url, params=params)
    if not data:
        return None
    hit = data[0]
    addr = hit.get("address", {})
    return GeoResult(
        lat=float(hit["lat"]),
        lon=float(hit["lon"]),
        display_name=hit.get("display_name"),
        plz=addr.get("postcode") or loc.plz,
        ort=addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or loc.ort,
        bundesland=addr.get("state") or loc.bundesland,
        confidence=float(hit.get("importance", 0.0) or 0.0),
        source="nominatim",
    )


def _build_query(extraction: Extraction) -> str | None:
    loc = extraction.lage
    structured = ", ".join(
        p
        for p in [
            " ".join(x for x in [loc.strasse, loc.hausnummer] if x),
            " ".join(x for x in [loc.plz, loc.ort] if x),
        ]
        if p.strip()
    )
    if structured.strip():
        return structured
    # Fall back to free-text lage description for incomplete addresses (4.4c).
    if loc.lagebeschreibung:
        return loc.lagebeschreibung
    if loc.ort:
        return loc.ort
    return None
