"""Demographic / economic facts via Wikidata (municipality-level)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.pipeline.enrichment.cache import request_json

logger = logging.getLogger(__name__)
settings = get_settings()


async def fetch_demographics(ort: str | None) -> dict[str, Any]:
    """Look up population (and basic facts) for a German municipality."""
    if not ort:
        return {}

    # 1) Resolve the municipality to a Wikidata entity.
    entity_id = await _search_entity(ort)
    if not entity_id:
        return {"ort": ort, "found": False}

    # 2) Fetch claims (population P1082).
    claims = await _fetch_claims(entity_id)
    population = _latest_population(claims)
    return {
        "ort": ort,
        "found": True,
        "wikidata_id": entity_id,
        "population": population,
        "source": "wikidata",
    }


async def _search_entity(ort: str) -> str | None:
    params = {
        "action": "wbsearchentities",
        "search": ort,
        "language": "de",
        "format": "json",
        "type": "item",
        "limit": 1,
    }
    url = f"{settings.wikidata_base_url}/w/api.php"
    payload = await request_json("GET", url, params=params)
    results = (payload or {}).get("search", [])
    return results[0]["id"] if results else None


async def _fetch_claims(entity_id: str) -> dict[str, Any]:
    params = {
        "action": "wbgetclaims",
        "entity": entity_id,
        "property": "P1082",  # population
        "format": "json",
    }
    url = f"{settings.wikidata_base_url}/w/api.php"
    payload = await request_json("GET", url, params=params)
    return (payload or {}).get("claims", {})


def _latest_population(claims: dict[str, Any]) -> int | None:
    entries = claims.get("P1082", [])
    best_year = -1
    best_val: int | None = None
    for entry in entries:
        try:
            amount = entry["mainsnak"]["datavalue"]["value"]["amount"]
            val = int(float(amount))
        except (KeyError, TypeError, ValueError):
            continue
        year = -1
        for qual in entry.get("qualifiers", {}).get("P585", []):
            try:
                time_str = qual["datavalue"]["value"]["time"]  # +2022-00-00T...
                year = int(time_str[1:5])
            except (KeyError, TypeError, ValueError):
                pass
        if year >= best_year:
            best_year = year
            best_val = val
    return best_val
