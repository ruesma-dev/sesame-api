# sesame_connector/domain/errors.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class SesameApiError(RuntimeError):
    method: str
    path: str
    status_code: int
    body: Any

    def __str__(self) -> str:
        preview = self.body
        try:
            if isinstance(preview, str) and len(preview) > 1200:
                preview = preview[:1200] + "…"
        except Exception:
            pass
        return f"Sesame API error: {self.method} {self.path} -> HTTP {self.status_code} body={preview!r}"


@dataclass(frozen=True, slots=True)
class EndpointNotConfiguredError(RuntimeError):
    key: str
    hint: Optional[str] = None

    def __str__(self) -> str:
        msg = f"Endpoint no configurado en endpoints.yaml: {self.key!r}"
        if self.hint:
            msg += f" ({self.hint})"
        return msg
