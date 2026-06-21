"""SQLAlchemy ORM models — the persistent source of truth.

Mirrors the ER diagram in ``docs/ARCHITECTURE.md``. Analysis results, prompt
traces and external-data snapshots are all persisted for full traceability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


def _uuid_col() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class Offer(Base):
    """A single inbound broker offer (one email + its attachments)."""

    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = _uuid_col()
    subject: Mapped[str | None] = mapped_column(Text)
    sender: Mapped[str | None] = mapped_column(Text)
    source_email: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    object_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan"
    )
    analysis: Mapped["Analysis | None"] = relationship(
        back_populates="offer", cascade="all, delete-orphan", uselist=False
    )
    replies: Mapped[list["Reply"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan"
    )
    matched_object: Mapped["KnownObject | None"] = relationship(
        back_populates="offers"
    )


class Document(Base):
    """A parsed attachment / email body belonging to an offer."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _uuid_col()
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str | None] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String(32), default="unknown")
    extracted_text: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    offer: Mapped[Offer] = relationship(back_populates="documents")


class KnownObject(Base):
    """A canonical real-estate object in the known registry (dedup target)."""

    __tablename__ = "objects"

    id: Mapped[uuid.UUID] = _uuid_col()
    address_raw: Mapped[str | None] = mapped_column(Text)
    address_norm: Mapped[str] = mapped_column(Text, index=True)
    plz: Mapped[str | None] = mapped_column(String(16))
    ort: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    dedup_key: Mapped[str | None] = mapped_column(Text, index=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    offers: Mapped[list[Offer]] = relationship(back_populates="matched_object")
    enrichments: Mapped[list["Enrichment"]] = relationship(
        back_populates="obj", cascade="all, delete-orphan"
    )


class Analysis(Base):
    """Extraction + enrichment + scoring result for an offer (with prompt trace)."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = _uuid_col()
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"), index=True, unique=True
    )
    extraction: Mapped[dict | None] = mapped_column(JSONB)
    enrichment: Mapped[dict | None] = mapped_column(JSONB)
    scoring: Mapped[dict | None] = mapped_column(JSONB)
    score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    band: Mapped[str | None] = mapped_column(String(16))
    llm_model: Mapped[str | None] = mapped_column(String(128))
    # prompt_trace = list of {system, user, model, params, raw_response, purpose}
    prompt_trace: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    offer: Mapped[Offer] = relationship(back_populates="analysis")


class Enrichment(Base):
    """A cached external-data snapshot for a known object."""

    __tablename__ = "enrichments"

    id: Mapped[uuid.UUID] = _uuid_col()
    object_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("objects.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(48), index=True)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    obj: Mapped[KnownObject] = relationship(back_populates="enrichments")


class Reply(Base):
    """A generated broker reply draft (e.g. 'object already known')."""

    __tablename__ = "replies"

    id: Mapped[uuid.UUID] = _uuid_col()
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"), index=True
    )
    language: Mapped[str] = mapped_column(String(8), default="de")
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    offer: Mapped[Offer] = relationship(back_populates="replies")
