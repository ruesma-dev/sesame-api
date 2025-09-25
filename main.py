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

    # ─────────────────────────────────────────────────────────────
    # FLAGS por pasos
    STEP_TOKEN_SMOKETEST = True           # <<< ejecuta solo el smoketest del token
    STEP_GET_WORK_ENTRIES_MONTH = False
    STEP_COMPANY_HOURS_REPORT = False
    STEP_HOURS_BAG_MONTH = False
    # ─────────────────────────────────────────────────────────────

    # Parámetros de ejemplo (para cuando actives otros pasos)
    YEAR = 2025
    MONTH = 9
    EMPLOYEE_ID = "9b58696a-d0d1-4294-b592-2f79a5436c77"

    try:
        if STEP_TOKEN_SMOKETEST:
            controller.run_token_smoketest()

        if STEP_GET_WORK_ENTRIES_MONTH:
            controller.run_get_work_entries_month(employee_id=EMPLOYEE_ID, year=YEAR, month=MONTH)

        if STEP_COMPANY_HOURS_REPORT:
            controller.run_company_hours_report_month(year=YEAR, month=MONTH)

        if STEP_HOURS_BAG_MONTH:
            controller.run_hours_bag_month(year=YEAR, month=MONTH, employee_ids=None)

    except Exception as exc:  # noqa: BLE001
        logging.getLogger("main").exception("Fallo en ejecución: %s", exc)
        sys.exit(1)
