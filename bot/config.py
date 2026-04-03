"""Centralized bot configuration loading."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parent.parent / ".env.bot.secret"


class BotConfig(BaseSettings):
    """Runtime settings for bot services and transports."""

    bot_token: str = ""
    lms_api_base_url: str = ""
    lms_api_key: str = ""
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_api_model: str = "coder-model"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_config() -> BotConfig:
    return BotConfig()
