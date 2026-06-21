# Copilot Instructions — Investa Offer Intelligence

AI-assisted triage, enrichment and 0–10 scoring of broker real-estate offers (email + PDF).
This file encodes project conventions so contributions stay consistent. See `docs/ARCHITECTURE.md`.

## Stack
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 / pydantic-settings.
- **DB:** PostgreSQL (extensions: `pg_trgm`; PostGIS optional). Access via async SQLAlchemy.
- **Frontend:** React + Vite + TypeScript + Tailwind, Recharts, TanStack Query.
- **LLM:** OpenAI-compatible client, default provider = **GitHub Models**. Never hardcode provider URLs/keys.
- **Packaging:** Docker Compose (`postgres`, `backend`, `frontend`). Must run with `docker compose up`.

## Hard rules
- **Never invent data.** Extraction prompts must return `null` for unknown fields + a `confidence` score.
- **Traceability is mandatory.** Every LLM call persists a `prompt_trace` = `{system, user, model, params, raw_response}` on the `analyses` row.
- **Prompts live in `backend/app/llm/prompts/`** as dedicated template files — never inline ad-hoc strings.
- **LLM + heuristics are separate.** Code computes hard numbers (yield, €/m², distances); the LLM does judgment (desirability, risks, narrative). Do not ask the LLM to do arithmetic.
- **Determinism:** low temperature (0–0.2) for extraction & scoring; use JSON/structured output mode.
- **Secrets only via `.env`**; keep `.env.example` commented and in sync with `config.py`.
- **Dedup:** normalize address → `pg_trgm` prefilter → RapidFuzz `token_sort_ratio` + geo Haversine. Store match evidence. Thresholds configurable.
- **Every external API call is cached** in the DB with `source` + `fetched_at` (Nominatim, Overpass, Wikidata, Mietspiegel seed). Respect rate limits; set a descriptive User-Agent.

## Conventions
- Type hints everywhere; `ruff` + `black` style. Async I/O for DB and HTTP (`httpx.AsyncClient`).
- Pydantic schemas in `backend/app/schemas/`; DB models in `backend/app/db/`.
- Pipeline modules in `backend/app/pipeline/` are pure-ish functions taking/returning Pydantic models.
- Pipeline status flow: `received → parsing → extracting → matching → enriching → scoring → done|failed` (persisted; frontend polls).
- Keep changes minimal and focused; do not add features beyond `docs/ARCHITECTURE.md` without noting it.
- Frontend talks to backend only through `/api/*`; data fetching via TanStack Query.

## Don't
- Don't use the Copilot subscription as an app LLM backend (license); use GitHub Models / OpenAI-compatible.
- Don't push to GitHub (the user pushes from a different account).
- Don't commit secrets, `.env`, large sample `.msg`/PDF binaries, or `node_modules`/`__pycache__`.
