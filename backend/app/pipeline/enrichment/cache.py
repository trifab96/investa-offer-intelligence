"""Shared HTTP client + DB-backed cache for external enrichment calls."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Enrichment

logger = logging.getLogger(__name__)
settings = get_settings()


def http_client() -> httpx.AsyncClient:
    """Async HTTP client with a descriptive User-Agent (API etiquette)."""
    return httpx.AsyncClient(
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept-Language": "de,en;q=0.8",
        },
        timeout=20.0,
        follow_redirects=True,
    )


# --------------------------------------------------------------------------- #
# Per-host throttling + retry with backoff (be a good public-API citizen)
# --------------------------------------------------------------------------- #
_host_locks: dict[str, asyncio.Lock] = {}
_host_last_call: dict[str, float] = {}


def _min_interval(host: str) -> float:
    if "nominatim" in host:
        return settings.nominatim_min_interval_s
    if "overpass" in host:
        return settings.overpass_min_interval_s
    if "wikidata" in host or "wikipedia" in host:
        return settings.wikidata_min_interval_s
    return 0.0


async def _throttle(host: str) -> None:
    """Serialize and space out requests to a host to respect its rate limits."""
    interval = _min_interval(host)
    if interval <= 0:
        return
    lock = _host_locks.setdefault(host, asyncio.Lock())
    async with lock:
        wait = interval - (time.monotonic() - _host_last_call.get(host, 0.0))
        if wait > 0:
            await asyncio.sleep(wait)
        _host_last_call[host] = time.monotonic()


_RETRYABLE = {403, 429, 500, 502, 503, 504}


async def request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> Any | None:
    """Throttled HTTP request with retry/backoff. Returns parsed JSON or None."""
    host = httpx.URL(url).host
    last_exc: Exception | None = None
    for attempt in range(settings.http_max_retries):
        try:
            await _throttle(host)
            async with http_client() as client:
                resp = await client.request(method, url, params=params, data=data)
            if resp.status_code in _RETRYABLE:
                backoff = settings.http_backoff_base ** (attempt + 1)
                logger.warning(
                    "%s %s -> %s (attempt %s/%s), backing off %.1fs",
                    method, host, resp.status_code, attempt + 1,
                    settings.http_max_retries, backoff,
                )
                await asyncio.sleep(backoff)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            await asyncio.sleep(settings.http_backoff_base ** (attempt + 1))
    logger.warning("Request to %s failed after retries: %s", host, last_exc)
    return None


async def get_cached(
    session: AsyncSession, object_id: uuid.UUID, source: str
) -> dict[str, Any] | None:
    """Return a fresh cached payload for (object, source) if within TTL."""
    ttl = timedelta(days=settings.enrichment_cache_ttl_days)
    cutoff = datetime.now(timezone.utc) - ttl
    row = (
        await session.execute(
            select(Enrichment)
            .where(
                Enrichment.object_id == object_id,
                Enrichment.source == source,
                Enrichment.fetched_at >= cutoff,
            )
            .order_by(Enrichment.fetched_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row.payload if row else None


async def store_cache(
    session: AsyncSession,
    object_id: uuid.UUID,
    source: str,
    payload: dict[str, Any],
) -> None:
    """Persist an enrichment payload for later reuse + auditability."""
    session.add(
        Enrichment(
            id=uuid.uuid4(),
            object_id=object_id,
            source=source,
            payload=payload,
        )
    )
    await session.flush()
