"""Application configuration loaded from environment variables / .env file."""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM provider ----
    # Supported: "gemini" | "openai" | "anthropic"
    llm_provider: Literal["gemini", "openai", "anthropic"] = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # Recommended model per provider (overridable via env).
    # Defaults verified against provider pricing pages, Nov 2026:
    #   gemini-3.5-flash-lite  $0.30 / $2.50 per 1M tokens (input/output)
    #   gpt-6.1-terra          $1.00 / $5.00 per 1M tokens
    #   claude-haiku-4-5       $1.00 / $5.00 per 1M tokens
    gemini_model: str = "gemini-3.5-flash-lite"
    openai_model: str = "gpt-6.1-terra"
    anthropic_model: str = "claude-haiku-4-5"

    # ---- Website fetching ----
    request_timeout_seconds: float = 20.0
    max_content_chars: int = 12000  # cap content sent to the LLM (cost control)
    max_page_bytes: int = 2_000_000  # cap download size

    # ---- Analysis caching (reduces repeated LLM cost) ----
    cache_ttl_seconds: int = 3600

    # ---- Server ----
    app_name: str = "AI Link Analysis API"


settings = Settings()
