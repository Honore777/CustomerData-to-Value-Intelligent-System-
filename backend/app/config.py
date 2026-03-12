"""
Application configuration.

Centralizes environment-driven settings so local development and production
deployment use the same code path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Always load this repository's root .env so background terminals and reload
# subprocesses do not accidentally pick up a stale DATABASE_URL from the shell.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _get_origins(value: str) -> List[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def _get_normalized_emails(value: str) -> List[str]:
    return [email.strip().lower() for email in value.split(",") if email.strip()]


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv(
            "APP_NAME",
            "Customer Churn Intelligent Prediction System",
        )
        self.app_env = os.getenv("APP_ENV", "development").strip().lower()
        self.debug = _get_bool("DEBUG", self.app_env != "production")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/supermarket_ai",
        )
        self.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")
        self.access_token_expire_minutes = _get_int(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            1440,
        )

        default_origins = (
            "http://localhost:3000,"
            "http://localhost:5173,"
            "http://127.0.0.1:3000,"
            "http://127.0.0.1:5173"
        )
        self.allowed_origins = _get_origins(
            os.getenv("ALLOWED_ORIGINS", default_origins)
        )
        self.platform_admin_emails = _get_normalized_emails(
            os.getenv("PLATFORM_ADMIN_EMAILS", "")
        )

        self.cookie_secure = _get_bool(
            "COOKIE_SECURE",
            self.app_env == "production",
        )
        self.cookie_samesite = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
        self.cookie_domain: Optional[str] = os.getenv("COOKIE_DOMAIN") or None

    def validate_for_startup(self) -> None:
        if self.app_env == "production" and self.secret_key == "change-this-in-production":
            raise RuntimeError("SECRET_KEY must be set in production.")

        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise RuntimeError("COOKIE_SAMESITE must be one of: lax, strict, none.")


settings = Settings()