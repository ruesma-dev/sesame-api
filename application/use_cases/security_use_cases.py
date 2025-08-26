# application/use_cases/security_use_cases.py
from __future__ import annotations

from application.interfaces.sesame_port import SesamePort
from domain.models.token_info import TokenInfo


class SecurityUseCases:
    """Casos de uso de seguridad (validación de token, compañía, etc.)."""

    def __init__(self, sesame_repo: SesamePort) -> None:
        self._repo = sesame_repo

    def show_token_info(self) -> TokenInfo:
        return self._repo.get_token_info()
