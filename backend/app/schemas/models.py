"""Pydantic schemas shared across the pipeline and API.

These model the structured data produced by each stage. The LLM extraction is
validated against :class:`Extraction`, guaranteeing ``null`` for unknowns and a
confidence score (never hallucinated values).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Extraction (4.4a) — strict structured output from the LLM
# --------------------------------------------------------------------------- #
class Location(BaseModel):
    strasse: str | None = None
    hausnummer: str | None = None
    plz: str | None = None
    ort: str | None = None
    bundesland: str | None = None
    lagebeschreibung: str | None = None


class Size(BaseModel):
    grundstueck_m2: float | None = None
    wohnflaeche_m2: float | None = None
    nutzflaeche_m2: float | None = None
    einheiten: int | None = None


class Price(BaseModel):
    betrag: float | None = None
    waehrung: str | None = "EUR"
    basis: str | None = None  # e.g. "Kaufpreis", "VHB"


class Extraction(BaseModel):
    """Facts extracted from an offer. Unknown fields MUST be null."""

    objektart: str | None = None
    lage: Location = Field(default_factory=Location)
    groesse: Size = Field(default_factory=Size)
    kaufpreis: Price = Field(default_factory=Price)
    zustand: str | None = None
    baujahr: int | None = None
    nutzungsmoeglichkeiten: list[str] = Field(default_factory=list)
    miete_ist_jahr: float | None = None
    miete_soll_jahr: float | None = None
    rendite_angegeben_pct: float | None = None
    vermietungsstand_pct: float | None = None  # occupancy 0-100
    geplante_einheiten: int | None = None  # planned units for development land
    makler: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str | None = None


# --------------------------------------------------------------------------- #
# Enrichment (4.4b)
# --------------------------------------------------------------------------- #
class GeoResult(BaseModel):
    lat: float | None = None
    lon: float | None = None
    display_name: str | None = None
    plz: str | None = None
    ort: str | None = None
    bundesland: str | None = None
    confidence: float = 0.0
    source: str = "nominatim"


class EnrichmentBundle(BaseModel):
    geo: GeoResult | None = None
    poi: dict[str, Any] | None = None
    demographics: dict[str, Any] | None = None
    rent_benchmark: dict[str, Any] | None = None
    image_analysis: dict[str, Any] | None = None
    sources: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Image analysis (4.4c — optional)
# --------------------------------------------------------------------------- #
class VisionAnalysis(BaseModel):
    bildtypen: list[str] = Field(default_factory=list)
    objekt_sichtbar: str | None = None
    zustand_visuell: str | None = None
    umgebung: str | None = None
    auffaelligkeiten: list[str] = Field(default_factory=list)
    visuelle_risiken: list[str] = Field(default_factory=list)
    visuelle_chancen: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    images_analyzed: int = 0



# --------------------------------------------------------------------------- #
# Scoring (4.5)
# --------------------------------------------------------------------------- #
class SubScore(BaseModel):
    name: str
    value: float = Field(ge=0.0, le=10.0)
    weight: float
    kind: Literal["heuristic", "llm"]
    rationale: str | None = None
    inputs: dict[str, Any] | None = None


class Driver(BaseModel):
    """A key influence factor on the score (the 'Top Treiber' of 4.5)."""

    name: str
    direction: Literal["positive", "negative"]
    impact: float  # signed weighted contribution vs. neutral baseline
    detail: str | None = None


class Scoring(BaseModel):
    score: float = Field(ge=0.0, le=10.0)
    band: Literal["reject", "review", "pursue"]
    asset_class: str | None = None
    asset_class_label: str | None = None
    subscores: list[SubScore] = Field(default_factory=list)
    top_drivers: list[Driver] = Field(default_factory=list)
    risk_penalty: float = 0.0
    rationale: str | None = None
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Dedup (4.2)
# --------------------------------------------------------------------------- #
class MatchEvidence(BaseModel):
    is_match: bool
    needs_review: bool = False
    matched_object_id: uuid.UUID | None = None
    address_similarity: float | None = None
    geo_distance_m: float | None = None
    reason: str | None = None


# --------------------------------------------------------------------------- #
# API responses
# --------------------------------------------------------------------------- #
class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str | None
    doc_type: str
    extracted_text: str | None = None
    char_count: int = 0

    model_config = {"from_attributes": True}


class ReplyOut(BaseModel):
    id: uuid.UUID
    language: str
    subject: str | None
    body: str | None
    reason: str | None

    model_config = {"from_attributes": True}


class OfferSummary(BaseModel):
    id: uuid.UUID
    subject: str | None
    sender: str | None
    status: str
    score: float | None = None
    band: str | None = None
    is_known: bool = False
    objektart: str | None = None
    ort: str | None = None
    created_at: datetime


class OfferDetail(BaseModel):
    id: uuid.UUID
    subject: str | None
    sender: str | None
    status: str
    error: str | None = None
    is_known: bool = False
    documents: list[DocumentOut] = Field(default_factory=list)
    extraction: dict[str, Any] | None = None
    enrichment: dict[str, Any] | None = None
    scoring: dict[str, Any] | None = None
    score: float | None = None
    band: str | None = None
    prompt_trace: list[dict[str, Any]] | None = None
    replies: list[ReplyOut] = Field(default_factory=list)
    created_at: datetime


class StatusOut(BaseModel):
    id: uuid.UUID
    status: str
    error: str | None = None


class PreviewPage(BaseModel):
    filename: str
    doc_type: str
    page: int
    image: str  # base64 PNG data URL


class PreviewOut(BaseModel):
    pages: list[PreviewPage] = Field(default_factory=list)
    note: str | None = None


class PortfolioStats(BaseModel):
    total: int = 0
    done: int = 0
    processing: int = 0
    failed: int = 0
    known_duplicates: int = 0
    scored: int = 0
    avg_score: float | None = None
    band_counts: dict[str, int] = Field(default_factory=dict)
    score_histogram: list[int] = Field(default_factory=list)  # 10 buckets 0-1..9-10
    top_offers: list[OfferSummary] = Field(default_factory=list)

