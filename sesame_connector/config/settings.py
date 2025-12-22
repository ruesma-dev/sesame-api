# sesame_connector/config/settings.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    sesame_base_url: str
    sesame_api_key: str
    sesame_auth_scheme: str = "Bearer"
    request_timeout_seconds: int = 30
    log_level: str = "INFO"
    tz_name: str = "Europe/Madrid"
    debug_http: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Variables esperadas (.env):
          - SESAME_BASE_URL
          - SESAME_API_KEY
          - SESAME_AUTH_SCHEME (opcional)
          - REQUEST_TIMEOUT_SECONDS (opcional)
          - LOG_LEVEL (opcional)
          - TZ_NAME (opcional)
          - SESAME_DEBUG_HTTP (opcional: 0/1)
        """
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv()
        except Exception:
            pass

        base_url = (os.getenv("SESAME_BASE_URL") or "").strip().rstrip("/")
        api_key = (os.getenv("SESAME_API_KEY") or "").strip()

        if not base_url:
            raise RuntimeError("Falta SESAME_BASE_URL en el entorno (.env).")
        if not api_key:
            raise RuntimeError("Falta SESAME_API_KEY en el entorno (.env).")

        auth_scheme = (os.getenv("SESAME_AUTH_SCHEME") or "Bearer").strip() or "Bearer"

        try:
            timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        except Exception:
            timeout = 30

        log_level = (os.getenv("LOG_LEVEL") or "INFO").strip() or "INFO"
        tz_name = (os.getenv("TZ_NAME") or "Europe/Madrid").strip() or "Europe/Madrid"

        debug_http_raw = (os.getenv("SESAME_DEBUG_HTTP") or "0").strip()
        debug_http = debug_http_raw in ("1", "true", "True", "yes", "YES")

        return cls(
            sesame_base_url=base_url,
            sesame_api_key=api_key,
            sesame_auth_scheme=auth_scheme,
            request_timeout_seconds=timeout,
            log_level=log_level,
            tz_name=tz_name,
            debug_http=debug_http,
        )
