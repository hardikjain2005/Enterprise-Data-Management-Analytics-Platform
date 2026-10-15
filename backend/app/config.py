"""Application settings, read from environment variables (.env file in the project root)."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    db_host: str = os.getenv("DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_name: str = os.getenv("DB_NAME", "enterprise_data_platform")
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    # Comma-separated list of origins allowed to call the API from a browser
    cors_origins: list[str] = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")


settings = Settings()
