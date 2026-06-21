"""Provider-agnostic LLM client (OpenAI-compatible) with prompt tracing.

Default provider is GitHub Models; swapping to OpenAI/Azure only requires
changing the ``LLM_*`` environment variables. Every call returns the parsed
result **and** a trace dict ``{system, user, model, params, raw_response,
purpose}`` so prompt engineering is fully auditable (persisted on the analysis).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    """Thin async wrapper around an OpenAI-compatible chat completions API."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries,
        )

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        purpose: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Run a chat completion expecting a JSON object.

        Returns ``(parsed_json, trace)``. ``trace`` is always returned, even on
        failure, so the (partial) prompt is still auditable.
        """
        model = model or settings.llm_chat_model
        temperature = settings.llm_temperature if temperature is None else temperature
        params = {"temperature": temperature, "response_format": {"type": "json_object"}}

        trace: dict[str, Any] = {
            "purpose": purpose,
            "model": model,
            "system": system,
            "user": user,
            "params": params,
            "raw_response": None,
        }
        try:
            resp = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **params,
            )
            content = resp.choices[0].message.content or "{}"
            trace["raw_response"] = content
            parsed = json.loads(content)
            return parsed, trace
        except Exception as exc:  # noqa: BLE001 — surface failure to caller + trace
            logger.warning("LLM call failed (%s): %s", purpose, exc)
            trace["raw_response"] = f"ERROR: {exc}"
            return {}, trace

    async def complete_vision_json(
        self,
        *,
        system: str,
        user: str,
        images: list[str],
        purpose: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Run a multimodal chat completion (text + images) expecting JSON.

        ``images`` are base64 data URLs (``data:image/png;base64,...``). Returns
        ``(parsed_json, trace)``; the trace records how many images were sent.
        """
        model = model or settings.llm_vision_model
        temperature = settings.llm_temperature if temperature is None else temperature
        params = {"temperature": temperature, "response_format": {"type": "json_object"}}

        content: list[dict[str, Any]] = [{"type": "text", "text": user}]
        for data_url in images:
            content.append({"type": "image_url", "image_url": {"url": data_url}})

        trace: dict[str, Any] = {
            "purpose": purpose,
            "model": model,
            "system": system,
            "user": f"{user}\n[+{len(images)} image(s) attached]",
            "params": params,
            "raw_response": None,
        }
        try:
            resp = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ],
                **params,
            )
            raw = resp.choices[0].message.content or "{}"
            trace["raw_response"] = raw
            return json.loads(raw), trace
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vision LLM call failed (%s): %s", purpose, exc)
            trace["raw_response"] = f"ERROR: {exc}"
            return {}, trace

    async def complete_text(
        self,
        *,
        system: str,
        user: str,
        purpose: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Run a chat completion expecting free-form text (e.g. a broker reply)."""
        model = model or settings.llm_chat_model
        temperature = settings.llm_temperature if temperature is None else temperature
        params = {"temperature": temperature}

        trace: dict[str, Any] = {
            "purpose": purpose,
            "model": model,
            "system": system,
            "user": user,
            "params": params,
            "raw_response": None,
        }
        try:
            resp = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **params,
            )
            content = resp.choices[0].message.content or ""
            trace["raw_response"] = content
            return content, trace
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed (%s): %s", purpose, exc)
            trace["raw_response"] = f"ERROR: {exc}"
            return "", trace


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """Return a process-wide LLM client singleton."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
