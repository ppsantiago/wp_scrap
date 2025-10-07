"""Application configuration for AI report generation."""
from __future__ import annotations

from functools import lru_cache
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:  # pragma: no cover - fallback for entornos sin pydantic-settings
    from pydantic import BaseSettings, Field  # type: ignore


class Settings(BaseSettings):
    """Runtime configuration values loaded from environment variables."""

    lmstudio_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        alias="LMSTUDIO_BASE_URL",
        description="Base URL del endpoint LMStudio compatible con OpenAI.",
    )
    lmstudio_api_key: str | None = Field(
        default=None,
        alias="LMSTUDIO_API_KEY",
        description="Clave de autenticación para LMStudio (si aplica).",
    )
    lmstudio_model: str = Field(
        default="openai/gpt-oss-20b",
        alias="LMSTUDIO_MODEL",
        description="Modelo por defecto utilizado para generar reportes IA.",
    )
    report_generation_timeout: float = Field(
        default=60.0,
        alias="REPORT_GENERATION_TIMEOUT",
        description="Timeout en segundos para llamadas al proveedor IA.",
    )
    report_generation_max_retries: int = Field(
        default=2,
        alias="REPORT_GENERATION_MAX_RETRIES",
        description="Cantidad máxima de reintentos al generar reportes IA.",
    )
    report_generation_cache_ttl_minutes: int = Field(
        default=1440,
        alias="REPORT_GENERATION_CACHE_TTL_MINUTES",
        description="Tiempo en minutos para reutilizar resultados cacheados.",
    )
    report_generation_temperature: float = Field(
        default=0.2,
        alias="REPORT_GENERATION_TEMPERATURE",
        description="Temperatura por defecto para la generación IA.",
    )
    report_generation_audience: str = Field(
        default="WP Scrap",
        alias="REPORT_GENERATION_AUDIENCE",
        description="Nombre de la audiencia objetivo para personalizar prompts.",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True


@lru_cache()
def get_settings() -> Settings:
    """Retorna instancia memoizada de configuración."""

    return Settings()


settings = get_settings()
