"""Runtime configuration for the LangGraph stock analysis system."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    temperature: float
    max_verification_retries: int
    default_track_interval_minutes: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            max_verification_retries=int(os.getenv("MAX_VERIFICATION_RETRIES", "2")),
            default_track_interval_minutes=int(os.getenv("DEFAULT_TRACK_INTERVAL_MINUTES", "5")),
        )


settings = Settings.from_env()
