"""Application configuration loaded from environment / .env (pydantic-settings).

All runtime configuration funnels through :class:`Settings`. Keep this in sync
with ``.env.example``. Never hardcode secrets or provider URLs elsewhere.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- LLM (OpenAI-compatible; default provider = GitHub Models) ----
    llm_base_url: str = "https://models.github.ai/inference"
    llm_api_key: str = "set-me"
    llm_chat_model: str = "openai/gpt-4o-mini"
    llm_vision_model: str = "openai/gpt-4o"
    llm_temperature: float = 0.1
    llm_request_timeout: int = 60
    llm_max_retries: int = 3
    # Image analysis (optional, 4.4c). 0 disables it.
    vision_enabled: bool = True
    vision_max_images: int = 4

    # ---- Database ----
    database_url: str = (
        "postgresql+psycopg://investa:change-me-in-prod@localhost:5432/offers"
    )

    # ---- External data sources ----
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"
    wikidata_base_url: str = "https://www.wikidata.org"
    wikipedia_base_url: str = "https://de.wikipedia.org"
    http_user_agent: str = "InvestaOfferIntel/0.1 (KI Challenge prototype)"
    enrichment_cache_ttl_days: int = 30
    # Rate-limiting / resilience for public APIs (Nominatim asks for <=1 req/s).
    http_max_retries: int = 3
    http_backoff_base: float = 1.5
    nominatim_min_interval_s: float = 1.1
    overpass_min_interval_s: float = 1.0
    wikidata_min_interval_s: float = 0.5

    # ---- Dedup thresholds ----
    dedup_address_sim_strong: float = 0.88
    dedup_address_sim_weak: float = 0.75
    dedup_geo_distance_m: float = 150.0

    # ---- Scoring weights ----
    score_weight_location: float = 0.30
    score_weight_price: float = 0.30
    score_weight_condition: float = 0.15
    score_weight_size_usage: float = 0.15
    score_weight_completeness: float = 0.10

    # ---- App / API ----
    api_port: int = 8000
    upload_dir: str = "/data/uploads"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def score_weights(self) -> dict[str, float]:
        return {
            "location": self.score_weight_location,
            "price_vs_market": self.score_weight_price,
            "condition": self.score_weight_condition,
            "size_usage": self.score_weight_size_usage,
            "data_completeness": self.score_weight_completeness,
        }


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
