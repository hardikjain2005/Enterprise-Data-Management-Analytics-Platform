"""Shared settings for the ETL scripts: paths and the database connection."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ETL_DIR = PROJECT_ROOT / "etl"
DEFAULT_DATA_DIR = ETL_DIR / "data" / "raw"
LOG_DIR = ETL_DIR / "logs"
REJECTED_DIR = ETL_DIR / "output" / "rejected"

# Credentials come from the .env file (never hard-coded in the code).
load_dotenv(PROJECT_ROOT / ".env")


def get_engine():
    """Create a SQLAlchemy engine for MySQL using the PyMySQL driver."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True)
