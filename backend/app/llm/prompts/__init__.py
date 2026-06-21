"""Prompt template loader.

Prompts live as plain ``.txt`` files in this directory so they are versioned,
reviewable and traceable (never inline ad-hoc strings). Templates use Python
``str.format`` placeholders. See ``docs/PROMPTS.md`` for the catalog + the
prompt-engineering techniques applied.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@lru_cache
def load_prompt(name: str) -> str:
    """Load a prompt template by file name (without extension)."""
    path = _PROMPT_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def render(name: str, **kwargs: object) -> str:
    """Load and fill a prompt template with the given placeholders."""
    return load_prompt(name).format(**kwargs)
