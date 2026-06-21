"""Broker reply generation (4.2): draft a German reply for known objects."""

from __future__ import annotations

from typing import Any

from app.llm.client import get_llm
from app.llm.prompts import load_prompt, render
from app.schemas.models import Extraction, MatchEvidence


async def draft_known_reply(
    subject: str | None,
    extraction: Extraction,
    match: MatchEvidence,
) -> tuple[str, dict[str, Any]]:
    """Draft a polite 'object already known, no commission' reply (not sent)."""
    loc = extraction.lage
    adresse = (
        " ".join(p for p in [loc.strasse, loc.hausnummer, loc.plz, loc.ort] if p)
        or loc.lagebeschreibung
        or "k. A."
    )
    system = load_prompt("reply_known_system")
    user = render(
        "reply_known_user",
        subject=subject or "Ihr Angebot",
        makler=extraction.makler or "Sehr geehrte Damen und Herren",
        objektart=extraction.objektart or "Objekt",
        ort=loc.ort or "k. A.",
        adresse=adresse,
        match_reason=match.reason or "intern bereits erfasst",
    )
    body, trace = await get_llm().complete_text(
        system=system, user=user, purpose="reply_known", temperature=0.3
    )
    return body, trace
