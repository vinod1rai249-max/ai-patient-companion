"""Application configuration."""

from functools import lru_cache
from os import getenv
from typing import Literal

from pydantic import BaseModel, ConfigDict

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


class Settings(BaseModel):
    """Central application settings loaded from environment variables."""

    app_name: str = "AI Companion for Patients"
    env: str = "local"
    database_url: str = "sqlite:///./data/ai_patient_companion.db"
    llm_provider: Literal["deterministic", "openrouter"] = "deterministic"
    openai_api_key: str = ""
    openai_model: str = "openai/gpt-4o-mini"
    openai_base_url: str = "https://openrouter.ai/api/v1"
    llm_timeout_seconds: int = 30
    log_level: str = "INFO"

    model_config = ConfigDict(extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for reuse across the app."""

    return Settings(
        app_name=getenv("APP_NAME", "AI Companion for Patients"),
        env=getenv("ENV", "local"),
        database_url=getenv("DATABASE_URL", "sqlite:///./data/ai_patient_companion.db"),
        llm_provider=getenv("LLM_PROVIDER", "deterministic"),
        openai_api_key=getenv("OPENAI_API_KEY", ""),
        openai_model=getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
        openai_base_url=getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        llm_timeout_seconds=int(getenv("LLM_TIMEOUT_SECONDS", "30")),
        log_level=getenv("LOG_LEVEL", "INFO"),
    )
