"""Micro-location signals via the Overpass API (OSM POIs within a radius)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.pipeline.enrichment.cache import request_json

logger = logging.getLogger(__name__)
settings = get_settings()

# Categories counted within the radius -> proxy for micro-location quality.
_CATEGORIES = {
    "public_transport": '["public_transport"]',
    "school": '["amenity"="school"]',
    "kindergarten": '["amenity"="kindergarten"]',
    "supermarket": '["shop"="supermarket"]',
    "doctor": '["amenity"="doctors"]',
    "pharmacy": '["amenity"="pharmacy"]',
    "restaurant": '["amenity"="restaurant"]',
    "park": '["leisure"="park"]',
}


async def fetch_pois(lat: float, lon: float, radius_m: int = 1000) -> dict[str, Any]:
    """Count nearby POIs by category around (lat, lon)."""
    # Fetch tagged nodes in one query and count them client-side by category.
    query = (
        "[out:json][timeout:25];("
        + "".join(
            f"node(around:{radius_m},{lat},{lon}){sel};"
            for sel in _CATEGORIES.values()
        )
        + ");out tags;"
    )
    payload = await request_json(
        "POST", settings.overpass_base_url, data={"data": query}
    )
    if payload is None:
        return {"radius_m": radius_m, "counts": {}, "total": 0, "error": "request_failed"}
    elements = payload.get("elements", [])

    counts = _classify(elements)
    return {
        "radius_m": radius_m,
        "counts": counts,
        "total": sum(counts.values()),
    }


def _classify(elements: list[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(_CATEGORIES, 0)
    for el in elements:
        tags = el.get("tags", {})
        if "public_transport" in tags:
            counts["public_transport"] += 1
        amenity = tags.get("amenity")
        if amenity in {"school", "kindergarten", "doctors", "pharmacy", "restaurant"}:
            key = "doctor" if amenity == "doctors" else amenity
            if key in counts:
                counts[key] += 1
        if tags.get("shop") == "supermarket":
            counts["supermarket"] += 1
        if tags.get("leisure") == "park":
            counts["park"] += 1
    return counts
