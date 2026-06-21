"""Tests for address normalization and geo distance."""

from app.pipeline.addressing import haversine_m, normalize_address, normalize_text
from app.schemas.models import Location


def test_normalize_text_expands_abbreviations():
    assert "strasse" in normalize_text("Bürgerstr. 44")
    assert "chaussee" in normalize_text("Schwanebecker Ch.")


def test_normalize_text_umlauts_and_punctuation():
    assert normalize_text("Bürgerstraße, 44!") == "buergerstrasse 44"


def test_normalize_address_uses_lagebeschreibung_fallback():
    loc = Location(lagebeschreibung="Nähe Hauptbahnhof Hamburg")
    out = normalize_address(loc)
    assert "hamburg" in out


def test_haversine_known_distance():
    # ~111 km between 1 degree of latitude.
    d = haversine_m(52.0, 13.0, 53.0, 13.0)
    assert 110_000 < d < 112_000


def test_haversine_zero():
    assert haversine_m(52.5, 13.4, 52.5, 13.4) == 0.0
