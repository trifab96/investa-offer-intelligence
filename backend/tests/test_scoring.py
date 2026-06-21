"""Tests for the heuristic parts of scoring (no LLM, no DB)."""

from app.pipeline.scoring import (
    _band,
    _buildability_subscore,
    _interpolate,
    _occupancy_subscore,
    _reversion_subscore,
    _risk_penalty,
    classify_asset,
    compute_metrics,
)
from app.schemas.models import (
    EnrichmentBundle,
    Extraction,
    Location,
    Price,
    Size,
)


def test_gross_yield_metric():
    ex = Extraction(
        kaufpreis=Price(betrag=1_000_000),
        miete_ist_jahr=50_000,
    )
    metrics = compute_metrics(ex, EnrichmentBundle())
    assert metrics["gross_yield_pct"] == 5.0


def test_price_per_m2_metric():
    ex = Extraction(
        kaufpreis=Price(betrag=600_000),
        groesse=Size(wohnflaeche_m2=120),
    )
    metrics = compute_metrics(ex, EnrichmentBundle())
    assert metrics["price_per_m2"] == 5000


def test_band_thresholds():
    assert _band(8.0) == "pursue"
    assert _band(5.0) == "review"
    assert _band(2.0) == "reject"


def test_interpolate_midpoint():
    points = [(2.0, 2.0), (6.0, 10.0)]
    assert _interpolate(4.0, points) == 6.0


def test_interpolate_clamps():
    points = [(2.0, 2.0), (6.0, 10.0)]
    assert _interpolate(0.0, points) == 2.0
    assert _interpolate(9.0, points) == 10.0


# --- Asset-class-aware scoring ------------------------------------------------
def test_classify_development_land():
    ex = Extraction(objektart="Wohnbaugrundstück", nutzungsmoeglichkeiten=["Neubau"])
    cls, _ = classify_asset(ex)
    assert cls == "development_land"


def test_classify_income_residential():
    ex = Extraction(objektart="Wohnanlage", nutzungsmoeglichkeiten=["Wohnen"])
    cls, _ = classify_asset(ex)
    assert cls == "income_residential"


def test_classify_commercial():
    ex = Extraction(objektart="Bürogebäude")
    cls, _ = classify_asset(ex)
    assert cls == "commercial"


def test_classify_generic_fallback():
    ex = Extraction(objektart="Sonstiges")
    cls, _ = classify_asset(ex)
    assert cls == "generic"


def test_occupancy_subscore_full_vs_vacant():
    full, _, _ = _occupancy_subscore(Extraction(vermietungsstand_pct=100))
    vacant, _, _ = _occupancy_subscore(Extraction(vermietungsstand_pct=50))
    assert full > vacant


def test_reversion_metric_and_subscore():
    ex = Extraction(miete_ist_jahr=100_000, miete_soll_jahr=120_000)
    metrics = compute_metrics(ex, EnrichmentBundle())
    assert metrics["reversion_pct"] == 20.0
    val, _, _ = _reversion_subscore(metrics)
    assert val > 5.0  # under-rented -> upside


def test_price_per_planned_unit():
    ex = Extraction(kaufpreis=Price(betrag=11_100_000), geplante_einheiten=111)
    metrics = compute_metrics(ex, EnrichmentBundle())
    assert metrics["price_per_planned_unit"] == 100_000


def test_buildability_more_units_better():
    ex_many = Extraction(geplante_einheiten=111)
    ex_few = Extraction(geplante_einheiten=4)
    many, _, _ = _buildability_subscore(ex_many, {})
    few, _, _ = _buildability_subscore(ex_few, {})
    assert many > few


def test_risk_penalty_severe_doubles():
    p_severe, hits = _risk_penalty(["Altlastenverdacht"])
    p_mild, _ = _risk_penalty(["unklare Lage"])
    assert p_severe > p_mild
    assert hits

