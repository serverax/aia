"""Runtime settings for the Hiring API.

Database env vars intentionally match ``libs.communication.postgres_client``
(``POSTGRES_*``) so the API, agents, and workers share one connection
convention. Nothing here carries a real secret default — production values
arrive via the admin-created Kubernetes Secret.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Service identity / telemetry
    service_name: str = "aia-hiring-api"
    environment: str = "dev"
    app_id: str = "hiring-api"  # used as audit actor when no user is attributed

    # Postgres (ordinoxai schema). Defaults mirror the dev convention; real
    # credentials come from the environment / mounted Secret.
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    db_schema: str = "ordinoxai"
    db_pool_min: int = 1
    db_pool_max: int = 10

    # AI scoring. When ANTHROPIC_API_KEY is absent the service falls back to a
    # deterministic heuristic scorer so the endpoint works offline and in CI.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # CORS origins for the web app (comma-separated). Empty => same-origin only.
    cors_origins: str = ""

    def dsn(self) -> str:
        pw = f":{self.postgres_password}" if self.postgres_password else ""
        return (
            f"postgresql://{self.postgres_user}{pw}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    """Process-wide singleton so env is read once."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
