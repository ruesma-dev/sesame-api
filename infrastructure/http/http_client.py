# infrastructure/http/http_client.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from config.settings import Settings


class HttpClient:
    def __init__(self, *, base_url: str, token: str, auth_scheme: str = "Bearer", timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.auth_scheme = auth_scheme or "Bearer"
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self._logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_settings(cls, settings: Settings) -> "HttpClient":
        return cls(
            base_url=settings.sesame_base_url,
            token=settings.sesame_api_key,
            auth_scheme=settings.sesame_auth_scheme,
            timeout_seconds=settings.request_timeout_seconds,
        )

    # Headers comunes
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.auth_scheme} {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # Helpers para loggear la URL completa ya preparada (con querystring)
    def _prepared_url(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = f"{self.base_url}{path}"
        req = requests.Request(method=method.upper(), url=url, params=params, headers=self._headers())
        prepped = req.prepare()
        return prepped.url  # type: ignore[return-value]

    # Métodos HTTP
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url_full = self._prepared_url("GET", path, params=params)
        self._logger.info("HTTP GET %s", url_full)
        return self.session.get(url_full, headers=self._headers(), timeout=self.timeout_seconds)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url_full = self._prepared_url("POST", path, params=params)
        self._logger.info("HTTP POST %s", url_full)
        return self.session.post(url_full, headers=self._headers(), json=json, timeout=self.timeout_seconds)

    def put(self, path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url_full = self._prepared_url("PUT", path, params=params)
        self._logger.info("HTTP PUT %s", url_full)
        return self.session.put(url_full, headers=self._headers(), json=json, timeout=self.timeout_seconds)

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url_full = self._prepared_url("DELETE", path, params=params)
        self._logger.info("HTTP DELETE %s", url_full)
        return self.session.delete(url_full, headers=self._headers(), timeout=self.timeout_seconds)
