"""Centralized application settings loaded from the project .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


def _read_env(name: str, default: str | None = None) -> str:
    """Read one environment value."""
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _read_int_env(name: str, default: int) -> int:
    """Read an integer environment variable."""
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Environment variable {name} must be an integer, got: {raw_value}"
        ) from exc


DB_HOST = _read_env("DB_HOST", "localhost")
DB_PORT = _read_int_env("DB_PORT", 5432)
DB_NAME = _read_env("DB_NAME", _read_env("POSTGRES_DB", "stormwatch"))
DB_USER = _read_env("DB_USER", _read_env("POSTGRES_USER", "stormwatch_user"))
DB_PASSWORD = _read_env("DB_PASSWORD", _read_env("POSTGRES_PASSWORD", ""))

if not DB_PASSWORD:
    raise ValueError(
        "DB_PASSWORD is not set. Check that your .env file contains "
        "the correct database credentials."
    )

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


def get_db_config() -> dict[str, str | int]:
    """Return database connection settings."""
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "url": DATABASE_URL,
        "sqlalchemy_url": SQLALCHEMY_DATABASE_URL,
    }






