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
    # Published pricing per 1M tokens (input / output):
    #   gemini-2.5-flash           $0.30 / $2.50
    #   gpt-4o-mini                $0.15 / $0.60
    #   claude-3-5-haiku-20241022  $1.00 / $5.00
    gemini_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-20241022"

    # ---- Website fetching ----
    request_timeout_seconds: float = 20.0
    max_content_chars: int = 12000  # cap content sent to the LLM (cost control)
    max_page_bytes: int = 2_000_000  # cap download size

    # ---- Analysis caching (reduces repeated LLM cost) ----
    cache_ttl_seconds: int = 3600

    # ---- Server ----
    app_name: str = "AI Link Analysis API"


settings = Settings()
