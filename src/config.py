"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM Configuration
    gemini_api_key: SecretStr | None = Field(default=None, description="Primary Google GenAI Key")
    openai_api_key: SecretStr | None = Field(default=None, description="OpenAI API Key (Legacy/Compat)")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="API Base URL",
    )
    llm_model: str = Field(
        default="gemini-2.5-flash",
        description="Primary Model name to use",
    )
    
    # Fallback Configuration (Optional)
    anthropic_api_key: SecretStr | None = Field(default=None, description="Backup Anthropic API Key")
    fallback_model: str | None = Field(default=None, description="Backup Model name")

    # GitHub Configuration
    github_token: SecretStr | None = Field(
        default=None,
        description="GitHub token for API fallback (optional but recommended)",
    )
    trending_language: str = Field(
        default="",
        description="Filter by language (empty for all)",
    )
    trending_since: Literal["daily", "weekly", "monthly"] = Field(
        default="daily",
        description="Trending time range",
    )
    max_repos: int = Field(default=15, ge=1, le=25)
    top_pick_count: int = Field(default=3, ge=1, le=5)

    # Notification Webhooks (all optional)
    feishu_webhook_url: str | None = Field(default=None)
    dingtalk_webhook_url: str | None = Field(default=None)
    slack_webhook_url: str | None = Field(default=None)
    telegram_bot_token: str | None = Field(default=None)
    telegram_chat_id: str | None = Field(default=None)

    # Output
    reports_dir: str = Field(default="reports")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
