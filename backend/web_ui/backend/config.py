"""
Configuration settings for the Stock Analysis Web UI Backend.
"""

import json
import logging
import os
from pathlib import Path
from typing import Annotated, Any, List

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    logging.warning(".env file not found at %s", env_path)

_DEFAULT_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8443",
    "http://127.0.0.1:8443",
]


def _normalize_origin(origin: str) -> str:
    """Browsers send Origin without a trailing slash — normalize env values."""
    return origin.strip().rstrip("/")


def _parse_cors_origins(raw: str) -> List[str]:
    """Parse CORS origins from JSON array or comma-separated string."""
    if not raw:
        return []
    stripped = raw.strip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [
                    _normalize_origin(str(part))
                    for part in parsed
                    if _normalize_origin(str(part))
                ]
        except json.JSONDecodeError:
            pass
    return [
        _normalize_origin(part)
        for part in stripped.split(",")
        if _normalize_origin(part)
    ]


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    app_name: str = "Stock Analysis Web UI"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000  # Backend port
    reload: bool = False

    # NoDecode: allow comma-separated CORS_ORIGINS on Render (not only JSON lists)
    cors_origins: Annotated[List[str], NoDecode] = list(_DEFAULT_CORS_ORIGINS)

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = "logs/backend.log"

    # Data directories
    data_dir: str = "data"
    logs_dir: str = "logs"
    temp_dir: str = "temp"

    # Portfolio settings
    portfolio_file: str = "data/portfolio.json"
    trades_file: str = "data/trades.json"

    # WebSocket settings
    websocket_ping_interval: int = 30  # seconds
    websocket_max_idle_minutes: int = 30
    websocket_max_connections: int = 100

    # Agent settings
    agent_timeout: int = 300  # seconds
    max_concurrent_queries: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return _parse_cors_origins(value) or list(_DEFAULT_CORS_ORIGINS)
        return value


def setup_directories() -> None:
    """Create necessary directories if they don't exist."""
    current = Settings()
    for directory in (current.data_dir, current.logs_dir, current.temp_dir):
        os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()