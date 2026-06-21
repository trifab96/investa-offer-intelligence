"""Local rent / price benchmark from a bundled seed dataset.

A documented simplification: there is no free, comprehensive Mietspiegel API,
so we ship a curated per-region CSV (reference cold rent EUR/m2 and indicative
buy price EUR/m2). Lookup is by full PLZ then PLZ prefix, with an Ort fallback.
"""

from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "mietspiegel_seed.csv"


@lru_cache
def _load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with _CSV_PATH.open(encoding="utf-8") as fh:
            # The seed file documents its columns only in a leading '#' comment,
            # so there is no header row -> provide field names explicitly.
            reader = csv.DictReader(
                (line for line in fh if not line.lstrip().startswith("#")),
                fieldnames=[
                    "plz_prefix",
                    "ort",
                    "bundesland",
                    "rent_eur_m2",
                    "buy_price_eur_m2",
                ],
            )
            for r in reader:
                rows.append(
                    {
                        "plz_prefix": r["plz_prefix"].strip(),
                        "ort": r["ort"].strip(),
                        "bundesland": r["bundesland"].strip(),
                        "rent_eur_m2": float(r["rent_eur_m2"]),
                        "buy_price_eur_m2": float(r["buy_price_eur_m2"]),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load mietspiegel seed: %s", exc)
    return rows


def lookup(plz: str | None, ort: str | None) -> dict[str, Any]:
    """Return the best rent/price benchmark for a PLZ or Ort."""
    rows = _load_rows()
    if not rows:
        return {"found": False}

    # 1) Longest PLZ-prefix match (e.g. exact 5-digit beats 2-digit region).
    if plz:
        digits = "".join(c for c in plz if c.isdigit())
        best: dict[str, Any] | None = None
        for row in rows:
            if digits.startswith(row["plz_prefix"]):
                if best is None or len(row["plz_prefix"]) > len(best["plz_prefix"]):
                    best = row
        if best:
            return _format(best, "plz_prefix")

    # 2) Ort fallback (case-insensitive contains).
    if ort:
        ort_l = ort.lower()
        for row in rows:
            if row["ort"].lower() in ort_l or ort_l in row["ort"].lower():
                return _format(row, "ort")

    return {"found": False}


def _format(row: dict[str, Any], match_by: str) -> dict[str, Any]:
    return {
        "found": True,
        "match_by": match_by,
        "region": row["ort"],
        "bundesland": row["bundesland"],
        "reference_rent_eur_m2_month": row["rent_eur_m2"],
        "reference_buy_price_eur_m2": row["buy_price_eur_m2"],
        "source": "mietspiegel_seed.csv",
    }
