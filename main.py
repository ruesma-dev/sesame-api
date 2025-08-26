# main.py
from __future__ import annotations

import logging
import sys

from application.use_cases.employee_use_cases import EmployeeUseCases
from application.use_cases.security_use_cases import SecurityUseCases
from config.settings import Settings
from infrastructure.http.http_client import HttpClient
from infrastructure.repositories.sesame_repository import SesameRepositoryImpl
from interface_adapters.controllers.cli_controller import CLIController


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_container() -> CLIController:
    # Carga todo de .env y config/endpoints.yaml
    settings = Settings.load()

    setup_logging(settings.log_level)
    logging.getLogger("main").info(
        "Sesame base_url=%s auth_scheme=%s timeout=%s",
        settings.sesame_base_url,
        settings.sesame_auth_scheme,
        settings.request_timeout_seconds,
    )

    http = HttpClient.from_settings(settings)
    sesame_repo = SesameRepositoryImpl(settings, http)
    employee_uc = EmployeeUseCases(sesame_repo)
    security_uc = SecurityUseCases(sesame_repo)
    return CLIController(employee_uc, security_uc)


if __name__ == "__main__":
    controller = build_container()
    try:
        # Cambia a True si quieres crear el empleado de demo
        controller.run_demo(create_demo=False)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("main").exception("Fallo en ejecución: %s", exc)
        sys.exit(1)
