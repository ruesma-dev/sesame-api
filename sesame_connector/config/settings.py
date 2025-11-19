# config/settings.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Sesión HTTP / Sesame (solo valores de conexión, NUNCA endpoints)
    sesame_base_url: str
    sesame_api_key: str
    sesame_auth_scheme: str = "Bearer"
    request_timeout_seconds: int = 30
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Carga configuración desde variables de entorno (.env si existe).
        Variables:
          - SESAME_BASE_URL (obligatoria), p.ej. https://api-eu4.sesametime.com
          - SESAME_API_KEY  (obligatoria)  → token
          - SESAME_AUTH_SCHEME (opcional)  → por defecto 'Bearer'
          - REQUEST_TIMEOUT_SECONDS (opcional, int) → por defecto 30
          - LOG_LEVEL (opcional) → por defecto 'INFO'
        """
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv()
        except Exception:
            pass

        base_url = (os.getenv("SESAME_BASE_URL") or "").strip()
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

        return cls(
            sesame_base_url=base_url.rstrip("/"),
            sesame_api_key=api_key,
            sesame_auth_scheme=auth_scheme,
            request_timeout_seconds=timeout,
            log_level=log_level,
        )
