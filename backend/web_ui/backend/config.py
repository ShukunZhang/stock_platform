"""
Configuration settings for the Stock Analysis Web UI Backend.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    # Don't log this as it may contain sensitive info
else:
    import logging
    logging.warning(f".env file not found at {env_path}")


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Stock Analysis Web UI"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000  # Backend port
    reload: bool = False
    
    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8443",
        "http://127.0.0.1:8443",
    ]
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


def setup_directories():
    """Create necessary directories if they don't exist."""
    settings = Settings()
    
    directories = [
        settings.data_dir,
        settings.logs_dir,
        settings.temp_dir
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()