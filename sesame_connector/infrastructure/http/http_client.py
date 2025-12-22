# sesame_connector/infrastructure/http/http_client.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from sesame_connector.config.settings import Settings


class HttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        auth_scheme: str = "Bearer",
        timeout_seconds: int = 30,
        debug_http: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._auth_scheme = auth_scheme or "Bearer"
        self._timeout_seconds = timeout_seconds
        self._debug_http = debug_http
        self._session = requests.Session()
        self._log = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_settings(cls, settings: Settings) -> "HttpClient":
        return cls(
            base_url=settings.sesame_base_url,
            token=settings.sesame_api_key,
            auth_scheme=settings.sesame_auth_scheme,
            timeout_seconds=settings.request_timeout_seconds,
            debug_http=settings.debug_http,
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self._auth_scheme} {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        url = self._url(path)
        self._log.info("HTTP %s %s", method.upper(), url)
        resp = self._session.request(
            method=method.upper(),
            url=url,
            headers=self._headers(),
            params=params,
            json=json_body,
            timeout=self._timeout_seconds,
        )

        ctype = resp.headers.get("Content-Type", "")
        self._log.info("HTTP %s ctype=%s", resp.status_code, ctype)

        if self._debug_http:
            try:
                self._log.info("Response JSON: %s", resp.json())
            except Exception:
                self._log.info("Response TEXT: %s", resp.text[:2000])

        return resp
