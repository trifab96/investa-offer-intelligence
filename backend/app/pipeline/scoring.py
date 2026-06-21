"""Scoring (4.5): hybrid heuristic + LLM, fully traceable.

Hard numbers (gross yield, EUR/m2, POI density, completeness) are computed in
code as heuristic sub-scores. Qualitative judgement (location desirability,
risks, opportunities, narrative) comes from the LLM. The final 0-10 score is a
configurable weighted blend; every sub-score keeps its inputs and rationale.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.llm.client import get_llm
from app.llm.prompts import load_prompt, render
from app.schemas.models import (
    Driver,
    EnrichmentBundle,
    Extraction,
    Scoring,
    SubScore,
)

logger = logging.getLogger(__name__)
settings = get_settings()

_CONFIG_PATH = Path(__file__).with_name("scoring.yaml")


@lru_cache
def _config() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Heuristic metrics (computed in code — never by the LLM)
# --------------------------------------------------------------------------- #
def compute_metrics(
    extraction: Extraction, enrichment: EnrichmentBundle
) -> dict[str, Any]:
    """Compute hard real-estate metrics used by heuristics and shown in the UI."""
    metrics: dict[str, Any] = {}
    price = extraction.kaufpreis.betrag
    rent = extraction.miete_ist_jahr or extraction.miete_soll_jahr

    if price and rent and price > 0:
        metrics["gross_yield_pct"] = round(rent / price * 100, 2)
    if price and extraction.groesse.wohnflaeche_m2:
        metrics["price_per_m2"] = round(price / extraction.groesse.wohnflaeche_m2, 0)
    elif price and extraction.groesse.grundstueck_m2:
        metrics["price_per_m2_land"] = round(
            price / extraction.groesse.grundstueck_m2, 0
        )

    rb = enrichment.rent_benchmark or {}
    if rb.get("found"):
        metrics["reference_rent_eur_m2_month"] = rb.get("reference_rent_eur_m2_month")
        metrics["reference_buy_price_eur_m2"] = rb.get("reference_buy_price_eur_m2")
        if metrics.get("price_per_m2") and rb.get("reference_buy_price_eur_m2"):
            metrics["price_vs_benchmark_pct"] = round(
                metrics["price_per_m2"] / rb["reference_buy_price_eur_m2"] * 100, 0
            )

    # Reversionary upside: current rent vs. potential (soll) rent, or vs. the
    # regional reference rent. Positive % means the asset is under-rented.
    ist = extraction.miete_ist_jahr
    soll = extraction.miete_soll_jahr
    if ist and soll and ist > 0:
        metrics["reversion_pct"] = round((soll - ist) / ist * 100, 1)
    elif (
        ist
        and extraction.groesse.wohnflaeche_m2
        and rb.get("reference_rent_eur_m2_month")
    ):
        current_rent_m2 = ist / 12 / extraction.groesse.wohnflaeche_m2
        ref = rb["reference_rent_eur_m2_month"]
        if current_rent_m2 > 0:
            metrics["current_rent_eur_m2_month"] = round(current_rent_m2, 2)
            metrics["reversion_pct"] = round((ref - current_rent_m2) / current_rent_m2 * 100, 1)

    # Development land: price per planned unit (the relevant land metric).
    units = extraction.geplante_einheiten or extraction.groesse.einheiten
    if price and units and units > 0:
        metrics["price_per_planned_unit"] = round(price / units, 0)

    return metrics


def _price_subscore(metrics: dict[str, Any]) -> tuple[float, str, dict[str, Any]]:
    """Price attractiveness from gross yield, else from price-vs-benchmark."""
    cfg = _config()["yield_score_breakpoints"]
    if "gross_yield_pct" in metrics:
        y = metrics["gross_yield_pct"]
        score = _interpolate(y, [(b["yield_pct"], b["score"]) for b in cfg])
        return score, f"gross yield {y}% mapped to {score:.1f}", {"gross_yield_pct": y}

    if "price_vs_benchmark_pct" in metrics:
        pct = metrics["price_vs_benchmark_pct"]
        # Below benchmark = cheaper = better. 100% -> 5; 70% -> 8; 130% -> 2.
        score = max(0.0, min(10.0, 5.0 + (100 - pct) / 10.0))
        return (
            score,
            f"price {pct:.0f}% of regional benchmark -> {score:.1f}",
            {"price_vs_benchmark_pct": pct},
        )
    return 5.0, "no price/yield data; neutral default", {}


def _location_subscore(
    enrichment: EnrichmentBundle, llm_location: float | None
) -> tuple[float, str, dict[str, Any]]:
    """Blend POI density (heuristic) with the LLM's desirability judgement."""
    poi = (enrichment.poi or {}).get("total", 0)
    # POI density 0..40+ -> 0..10 (saturating).
    poi_score = min(10.0, poi / 4.0)
    inputs: dict[str, Any] = {"poi_total": poi}
    if llm_location is not None:
        inputs["llm_location_desirability"] = llm_location
        blended = round(0.5 * poi_score + 0.5 * llm_location, 2)
        return blended, f"POI density {poi} + LLM {llm_location} -> {blended}", inputs
    return round(poi_score, 2), f"POI density {poi} -> {poi_score:.1f}", inputs


def _condition_subscore(extraction: Extraction) -> tuple[float, str, dict[str, Any]]:
    cond = (extraction.zustand or "").lower()
    table = _config()["condition_scores"]
    for key, val in table.items():
        if key in cond:
            return float(val), f"condition '{cond}' -> {val}", {"zustand": cond}
    return 5.0, "condition unknown; neutral default", {"zustand": cond or None}


def _size_usage_subscore(extraction: Extraction) -> tuple[float, str, dict[str, Any]]:
    usages = len(extraction.nutzungsmoeglichkeiten or [])
    has_units = bool(extraction.groesse.einheiten)
    base = 5.0 + min(3.0, usages * 1.0) + (1.0 if has_units else 0.0)
    score = min(10.0, base)
    return (
        score,
        f"{usages} usage option(s){' + units' if has_units else ''} -> {score:.1f}",
        {"usage_options": usages, "has_units": has_units},
    )


# --------------------------------------------------------------------------- #
# Asset-class classification + class-specific sub-scores
# --------------------------------------------------------------------------- #
def classify_asset(extraction: Extraction) -> tuple[str, str]:
    """Map an offer to an asset class using keyword rules from scoring.yaml.

    Returns (class_key, human_label). Falls back to 'generic' when unsure.
    """
    cfg = _config()
    keywords: dict[str, list[str]] = cfg.get("classification", {}).get("keywords", {})
    haystack = " ".join(
        [
            (extraction.objektart or "").lower(),
            " ".join(extraction.nutzungsmoeglichkeiten or []).lower(),
        ]
    )
    # development_land takes precedence (a plot may also mention "Wohnen").
    order = ["development_land", "commercial", "income_residential"]
    for cls in order:
        for kw in keywords.get(cls, []):
            if kw in haystack:
                label = cfg["profiles"].get(cls, {}).get("label", cls)
                return cls, label
    return "generic", cfg["profiles"]["generic"]["label"]


def _occupancy_subscore(extraction: Extraction) -> tuple[float, str, dict[str, Any]]:
    """Occupancy/lease status — the key risk metric for an income property."""
    occ = extraction.vermietungsstand_pct
    if occ is None:
        return 5.0, "Vermietungsstand unbekannt; neutraler Default", {"occupancy": None}
    # 100% -> 9, 90% -> 7.5, 70% -> 4.5, 50% -> 1.5 (linear-ish, clamped).
    score = max(0.0, min(10.0, (occ - 40) / 60 * 9.0))
    return round(score, 2), f"Vermietungsstand {occ:.0f}% -> {score:.1f}", {"occupancy": occ}


def _reversion_subscore(metrics: dict[str, Any]) -> tuple[float, str, dict[str, Any]]:
    """Reversionary upside: under-rented assets carry rent-growth potential."""
    rev = metrics.get("reversion_pct")
    if rev is None:
        return 5.0, "Kein Mietsteigerungspotenzial ableitbar; neutral", {"reversion_pct": None}
    # 0% -> 5, +20% -> 8, +40% -> 10; negative (over-rented) -> below 5.
    score = max(0.0, min(10.0, 5.0 + rev / 8.0))
    return (
        round(score, 2),
        f"Mietsteigerungspotenzial {rev:+.0f}% -> {score:.1f}",
        {"reversion_pct": rev},
    )


def _buildability_subscore(
    extraction: Extraction, metrics: dict[str, Any]
) -> tuple[float, str, dict[str, Any]]:
    """Development potential: planned units and price per buildable unit."""
    units = extraction.geplante_einheiten or extraction.groesse.einheiten
    ppu = metrics.get("price_per_planned_unit")
    inputs: dict[str, Any] = {"planned_units": units, "price_per_planned_unit": ppu}
    if not units:
        return 5.0, "Keine geplanten Einheiten angegeben; neutral", inputs
    # More units = more development potential; price/unit modulates it.
    unit_score = min(8.0, 4.0 + units / 25.0)
    if ppu:
        # cheaper land per unit is better: 50k/unit -> +2, 150k/unit -> 0, 300k -> -2
        unit_score += max(-2.0, min(2.0, (150_000 - ppu) / 50_000))
    score = max(0.0, min(10.0, unit_score))
    detail = f"{units} geplante Einheiten"
    if ppu:
        detail += f", {ppu:,.0f} €/Einheit"
    return round(score, 2), f"{detail} -> {score:.1f}", inputs


def _risk_penalty(risks: list[str]) -> tuple[float, list[str]]:
    """Convert qualitative LLM risks into a bounded score deduction."""
    cfg = _config().get("risk_penalty", {})
    per = cfg.get("per_risk", 0.4)
    cap = cfg.get("max_total", 2.0)
    severe = cfg.get("severe_keywords", [])
    total = 0.0
    hits: list[str] = []
    for r in risks:
        rl = r.lower()
        weight = 2.0 if any(s in rl for s in severe) else 1.0
        total += per * weight
        if weight > 1.0:
            hits.append(r)
    return min(cap, round(total, 2)), hits


def _completeness_subscore(
    extraction: Extraction,
) -> tuple[float, str, dict[str, Any]]:
    fields = [
        extraction.objektart,
        extraction.lage.ort,
        extraction.groesse.grundstueck_m2 or extraction.groesse.wohnflaeche_m2,
        extraction.kaufpreis.betrag,
        extraction.zustand,
    ]
    filled = sum(1 for f in fields if f)
    score = round(filled / len(fields) * 10, 1)
    return score, f"{filled}/{len(fields)} key fields present", {"filled": filled}


def _interpolate(x: float, points: list[tuple[float, float]]) -> float:
    points = sorted(points)
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return round(y0 + t * (y1 - y0), 2)
    return points[-1][1]


def _band(score: float) -> str:
    if score >= 7.0:
        return "pursue"
    if score >= 4.0:
        return "review"
    return "reject"


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
async def score_offer(
    extraction: Extraction, enrichment: EnrichmentBundle
) -> tuple[Scoring, dict[str, Any], dict[str, Any]]:
    """Return (scoring, metrics, llm_trace)."""
    metrics = compute_metrics(extraction, enrichment)

    # --- LLM qualitative judgement (no arithmetic) ---
    system = load_prompt("scoring_system")
    user = render(
        "scoring_user",
        extraction_json=extraction.model_dump_json(indent=2),
        enrichment_json=json.dumps(enrichment.model_dump(), ensure_ascii=False, indent=2),
        metrics_json=json.dumps(metrics, ensure_ascii=False, indent=2),
    )
    llm_out, trace = await get_llm().complete_json(
        system=system, user=user, purpose="scoring_qualitative"
    )
    llm_location = _safe_float(llm_out.get("location_desirability"))
    risks = list(llm_out.get("risks", []) or [])

    # --- Classify the asset, then build only the sub-scores its profile uses ---
    asset_class, asset_label = classify_asset(extraction)
    profile = _config()["profiles"].get(asset_class, _config()["profiles"]["generic"])
    profile_weights: dict[str, float] = profile["weights"]

    # Compute every candidate sub-score (value, rationale, inputs, kind).
    loc_val, loc_r, loc_in = _location_subscore(enrichment, llm_location)
    occ_val, occ_r, occ_in = _occupancy_subscore(extraction)
    rev_val, rev_r, rev_in = _reversion_subscore(metrics)
    build_val, build_r, build_in = _buildability_subscore(extraction, metrics)
    price_val, price_r, price_in = _price_subscore(metrics)
    cond_val, cond_r, cond_in = _condition_subscore(extraction)
    su_val, su_r, su_in = _size_usage_subscore(extraction)
    comp_val, comp_r, comp_in = _completeness_subscore(extraction)

    candidates: dict[str, tuple[float, str, dict[str, Any], str]] = {
        "location": (loc_val, llm_out.get("location_rationale") or loc_r, loc_in,
                     "llm" if llm_location is not None else "heuristic"),
        "occupancy": (occ_val, occ_r, occ_in, "heuristic"),
        "reversion": (rev_val, rev_r, rev_in, "heuristic"),
        "buildability": (build_val, build_r, build_in, "heuristic"),
        "price_vs_market": (price_val, price_r, price_in, "heuristic"),
        "condition": (cond_val, cond_r, cond_in, "heuristic"),
        "size_usage": (su_val, su_r, su_in, "heuristic"),
        "data_completeness": (comp_val, comp_r, comp_in, "heuristic"),
    }

    # Keep only the sub-scores this profile cares about.
    subs: list[SubScore] = []
    for name, weight in profile_weights.items():
        if name not in candidates:
            continue
        value, rationale, inputs, kind = candidates[name]
        subs.append(
            SubScore(
                name=name, value=value, weight=weight, kind=kind,  # type: ignore[arg-type]
                rationale=rationale, inputs=inputs,
            )
        )

    total_weight = sum(s.weight for s in subs) or 1.0
    weighted = sum(s.value * s.weight for s in subs) / total_weight

    # Risk penalty: structural flaws should pull the score down.
    penalty, severe_hits = _risk_penalty(risks)
    final = max(0.0, min(10.0, round(weighted - penalty, 2)))

    scoring = Scoring(
        score=final,
        band=_band(final),  # type: ignore[arg-type]
        asset_class=asset_class,
        asset_class_label=asset_label,
        subscores=subs,
        top_drivers=_top_drivers(subs, total_weight, penalty=penalty, severe=severe_hits),
        risk_penalty=penalty,
        rationale=llm_out.get("narrative"),
        risks=risks,
        opportunities=list(llm_out.get("opportunities", []) or []),
    )
    return scoring, metrics, trace


def _top_drivers(
    subs: list[SubScore],
    total_weight: float,
    top_n: int = 3,
    penalty: float = 0.0,
    severe: list[str] | None = None,
) -> list[Driver]:
    """Rank sub-scores by signed weighted deviation from the neutral baseline (5.0).

    This surfaces the key factors pushing the score up or down — the "Top Treiber"
    the challenge asks for (4.5). The risk penalty is included as a negative driver.
    """
    drivers: list[Driver] = []
    for s in subs:
        impact = round((s.value - 5.0) * s.weight / total_weight, 3)
        if abs(impact) < 1e-6:
            continue
        drivers.append(
            Driver(
                name=s.name,
                direction="positive" if impact > 0 else "negative",
                impact=impact,
                detail=s.rationale,
            )
        )
    if penalty > 0:
        detail = "Risikoabzug"
        if severe:
            detail += f" (u. a. {', '.join(severe[:2])})"
        drivers.append(
            Driver(name="risk_penalty", direction="negative", impact=-penalty, detail=detail)
        )
    drivers.sort(key=lambda d: abs(d.impact), reverse=True)
    return drivers[:top_n]



def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        v = float(value)
        return max(0.0, min(10.0, v))
    except (TypeError, ValueError):
        return None
