"""Application configuration, read from environment variables."""
import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/sampurna"
        )
        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-change-me-in-production-please")
        self.jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "720"))
        # Fernet key for interview transcripts (separately secured storage).
        self.transcript_key: str | None = os.getenv("TRANSCRIPT_ENCRYPTION_KEY")
        self.anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
        self.llm_model: str = os.getenv("SAMPURNA_LLM_MODEL", "claude-sonnet-5-5")
        self.cors_origins: list[str] = os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        self.min_group_size: int = int(os.getenv("MIN_AGGREGATE_GROUP_SIZE", "5"))
        self.review_interval_days: int = 90
        self.agent_max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
