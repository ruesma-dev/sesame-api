# infrastructure/http/http_client.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.settings import Settings

@dataclass
class HttpClient:
    base_url: str
    api_key: str
    auth_scheme: str
    timeout_seconds: int
    session: requests.Session
    logger: logging.Logger

    @classmethod
    def from_settings(cls, settings: Settings) -> "HttpClient":
        logger = logging.getLogger("http")
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        session = requests.Session()
        retry = Retry(
            total=5, backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH"], raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return cls(
            base_url=settings.sesame_base_url.rstrip("/"),
            api_key=settings.sesame_api_key,
            auth_scheme=settings.sesame_auth_scheme,
            timeout_seconds=settings.request_timeout_seconds,
            session=session,
            logger=logger,
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.auth_scheme} {self.api_key}".strip(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        self.logger.debug("GET %s params=%s", url, params)
        return self.session.get(url, headers=self._headers(), params=params, timeout=self.timeout_seconds)

    def post(self, path: str, json: Dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}{path}"
        self.logger.debug("POST %s json=%s", url, json)
        return self.session.post(url, headers=self._headers(), json=json, timeout=self.timeout_seconds)
