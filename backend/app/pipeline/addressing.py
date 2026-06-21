"""Address normalization + geo helpers shared by dedup and enrichment."""

from __future__ import annotations

import math
import re

from app.schemas.models import Location

_ABBREV = {
    # 'str.' is usually attached to the street name (Bürgerstr.) -> match the
    # 'str' token whether standalone or as a word-final suffix.
    r"str\.": "strasse",
    r"str\b": "strasse",
    r"\bch\.?\b": "chaussee",
    r"\bpl\.?\b": "platz",
}


def normalize_address(loc: Location) -> str:
    """Build a normalized, comparable address string from a Location."""
    parts = [
        loc.strasse or "",
        loc.hausnummer or "",
        loc.plz or "",
        loc.ort or "",
    ]
    raw = " ".join(p for p in parts if p)
    if not raw.strip() and loc.lagebeschreibung:
        raw = loc.lagebeschreibung
    return normalize_text(raw)


def normalize_text(raw: str) -> str:
    """Lowercase, expand common German address abbreviations, strip noise."""
    s = raw.lower()
    s = s.replace("ß", "ss")
    s = (
        s.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
    )
    for pattern, repl in _ABBREV.items():
        s = re.sub(pattern, repl, s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in metres."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))
