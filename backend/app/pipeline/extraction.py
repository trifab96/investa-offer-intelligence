"""Extraction (4.4a): turn raw offer text into a validated Extraction object.

Uses a single structured-output LLM call. The result is validated by the
:class:`Extraction` Pydantic schema, so unknown fields stay ``null`` and no
values are invented. Returns the extraction plus the prompt trace.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.llm.client import get_llm
from app.llm.prompts import load_prompt, render
from app.schemas.models import Extraction

logger = logging.getLogger(__name__)

# Truncate very long corpora to keep token usage / latency bounded for a prototype.
_MAX_CHARS = 24_000


async def extract_offer(offer_text: str) -> tuple[Extraction, dict[str, Any]]:
    """Extract structured facts from the combined offer text."""
    text = offer_text[:_MAX_CHARS]
    system = load_prompt("extraction_system")
    user = render("extraction_user", offer_text=text)

    parsed, trace = await get_llm().complete_json(
        system=system, user=user, purpose="extraction"
    )
    try:
        extraction = Extraction.model_validate(parsed)
    except ValidationError as exc:
        logger.warning("Extraction validation failed; using empty result: %s", exc)
        extraction = Extraction(confidence=0.0, notes="extraction_validation_failed")
    return extraction, trace
