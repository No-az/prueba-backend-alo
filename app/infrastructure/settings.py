from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del servicio, leída de variables de entorno (o de un .env local)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./credit_eval.db"

    # Límite de peticiones por IP. Formato de la librería `limits`: "30/minute".
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: str = "memory://"
    rate_limit_write: str = "30/minute"
    rate_limit_read: str = "120/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
