"""Configuration settings for TerraWatch API."""

from __future__ import annotations

import os
from typing import List


class Settings:
    HOST: str = os.getenv("TERRAWATCH_API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("TERRAWATCH_API_PORT", "8000"))
    DB_PATH: str = os.getenv("TERRAWATCH_DB_PATH", "terrawatch.db")
    MODE: str = os.getenv("TERRAWATCH_MODE", "live")

    # Person 5 web console origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",  # Permissive for hackathon local dev
    ]


settings = Settings()
