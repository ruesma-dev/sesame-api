# application/use_cases/security_use_cases.py
from __future__ import annotations

from typing import Any, Dict

from sesame_connector.application.interfaces.sesame_port import SesamePort


class SecurityUseCases:
    """
    Casos de uso de seguridad/autenticación contra Sesame.

    Delegan en el repositorio (SesamePort) para obtener la
    información del token y de la compañía.
    """

    def __init__(self, repo: SesamePort) -> None:
        self._repo = repo

    def show_token_info(self) -> Dict[str, Any]:
        """
        Devuelve la estructura dict con:
          base_url, auth_scheme, token_masked, parsed_company, raw_response
        """
        return self._repo.get_token_info()

    def show_company(self) -> Dict[str, Any]:
        """
        Devuelve solo la información básica de la compañía (id, name, language, notificationEmail).
        """
        return self._repo.get_company()
