"""
AutoMerge Backend Configuration

Centralized settings loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable binding."""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/automerge.db"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Optional: LLM integration
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # Optional: GitHub integration
    GITHUB_TOKEN: str | None = None
    GITHUB_OWNER: str | None = None
    GITHUB_REPO: str | None = None

    # Optional: Slack webhook
    SLACK_WEBHOOK_URL: str | None = None

    # Agent configuration
    AGENT_MAX_RETRIES: int = 3
    AGENT_TIMEOUT_SECONDS: int = 30
    DEMO_MODE: bool = True

    @property
    def has_llm(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.GEMINI_API_KEY)

    @property
    def has_github(self) -> bool:
        return bool(self.GITHUB_TOKEN and self.GITHUB_OWNER and self.GITHUB_REPO)

    @property
    def has_slack(self) -> bool:
        return bool(self.SLACK_WEBHOOK_URL)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton settings instance
settings = Settings()
