"""Tests for the Mietspiegel seed lookup."""

from app.pipeline.enrichment import mietspiegel


def test_lookup_by_exact_plz_prefix():
    result = mietspiegel.lookup("80331", "München")
    assert result["found"] is True
    assert result["bundesland"] == "Bayern"


def test_lookup_prefers_longer_prefix():
    # 21502 (Geesthacht) should beat the generic 21 (Hamburg) prefix.
    result = mietspiegel.lookup("21502", None)
    assert result["region"] == "Geesthacht"


def test_lookup_ort_fallback():
    result = mietspiegel.lookup(None, "Berlin")
    assert result["found"] is True


def test_lookup_miss():
    result = mietspiegel.lookup("99999", "Nirgendwo")
    assert result["found"] is False
