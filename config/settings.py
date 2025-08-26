# config/settings.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    sesame_base_url: str
    sesame_api_key: str
    sesame_auth_scheme: str
    request_timeout_seconds: int
    log_level: str
    endpoints: Dict[str, Any]

    @staticmethod
    def load() -> "Settings":
        endpoints_path = Path(__file__).parent / "endpoints.yaml"
        with endpoints_path.open("r", encoding="utf-8") as f:
            endpoints = yaml.safe_load(f) or {}
        return Settings(
            sesame_base_url=os.getenv("SESAME_BASE_URL", "https://app.sesametime.com"),
            sesame_api_key=os.getenv("SESAME_API_KEY", ""),
            sesame_auth_scheme=os.getenv("SESAME_AUTH_SCHEME", "Bearer"),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            endpoints=endpoints,
        )
