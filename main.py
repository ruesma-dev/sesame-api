# main.py
from __future__ import annotations

import logging
from pathlib import Path

from sesame_connector.config import Settings
from sesame_connector.config.endpoints_loader import load_endpoints
from sesame_connector.infrastructure.http.http_client import HttpClient
from sesame_connector.infrastructure.filesystem.csv_repository import CsvRepository
from sesame_connector.infrastructure.repositories import SesameRepositoryImpl
from sesame_connector.application.use_cases.security_use_cases import SecurityUseCases
from sesame_connector.application import EmployeeUseCases
from sesame_connector.interface_adapters.controllers.cli_controller import CLIController


def build_container() -> CLIController:
    # Cargar settings de .env (sin hardcodear credenciales)
    settings = Settings.from_env()

    # Cargar endpoints desde YAML
    endpoints = load_endpoints(Path("sesame_connector/config") / "endpoints.yaml")

    # Http client
    http = HttpClient.from_settings(settings)

    # Repo Sesame
    sesame_repo = SesameRepositoryImpl(settings, http, endpoints=endpoints)

    # CSV repo (usa nombres fijos como pediste en CsvRepository)
    csv_repo = CsvRepository(output_dir="output")

    # Use cases
    sec_uc = SecurityUseCases(sesame_repo)
    emp_uc = EmployeeUseCases(sesame_repo)

    # Controller
    return CLIController(sesame_repo, csv_repo, sec_uc, emp_uc)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("main")

    # ==== Parámetros por defecto (puedes cambiarlos rápido) ====
    YEAR = 2025
    MONTH = 9
    # Si quieres usar un empleado concreto para pruebas puntuales:
    EMPLOYEE_ID = "9b58696a-d0d1-4294-b592-2f79a5436c77"

    # ==== Flags para activar/desactivar pasos ====
    DO_SMOKETEST = True
    DO_EXPORT_EMPLOYEES = True
    DO_EXPORT_OFFICES = True
    DO_EXPORT_EMPLOYEE_OFFICE_ASSIGNATIONS = True  # << añadido
    DO_EXPORT_WORK_ENTRIES_ALL_MONTH = True        # todos los empleados (se mantiene)
    DO_AGGREGATES_FROM_WORK_ENTRIES = True         # coordinates / hours_by_employee / hours_by_office (se mantiene)
    DO_HOURS_BAG_MONTH = False                     # opcional, puede salir vacío según config actual
    DO_SINGLE_EMPLOYEE_WORK_ENTRIES = False        # por si quieres mantener pruebas con un empleado

    # NUEVO: Exportar estadísticas worked-hours por RANGO (17→29 sep-2025, inclusivo)
    DO_EXPORT_WORKED_HOURS_RANGE = True
    WITH_CHECKS = True  # ponlo a False si no necesitas los "checks" en la respuesta

    # NUEVO (mínima modificación): Exportar ausencias y vacaciones por el mismo rango
    DO_EXPORT_DAY_OFFS_RANGE = True

    # ==== Arranque ====
    settings = Settings.from_env()
    log.info(
        "Sesame base_url=%s auth_scheme=%s timeout=%s",
        settings.sesame_base_url,
        settings.sesame_auth_scheme,
        settings.request_timeout_seconds,
    )

    controller = build_container()

    # 1) Smoke test del token (mantener siempre como test rápido)
    if DO_SMOKETEST:
        controller.run_token_info_smoketest()

    # 2) Exportar empleados (CSV fijo: employees.csv)
    if DO_EXPORT_EMPLOYEES:
        controller.run_export_employees()

    # 3) Exportar oficinas (CSV fijo: offices.csv)
    if DO_EXPORT_OFFICES:
        controller.run_export_offices()

    # 4) NUEVO: Exportar asignaciones empleado–oficina (CSV fijo: employee_office_assignations.csv)
    if DO_EXPORT_EMPLOYEE_OFFICE_ASSIGNATIONS:
        controller.run_export_employee_office_assignations_all()

    # 5) Work entries de TODOS los empleados para el mes (CSV fijo: work_entries.csv)
    if DO_EXPORT_WORK_ENTRIES_ALL_MONTH:
        controller.run_export_work_entries_all_month(year=YEAR, month=MONTH)

    # 6) Agregados a partir de Work Entries (CSV fijos)
    if DO_AGGREGATES_FROM_WORK_ENTRIES:
        controller.run_company_hours_report_month(year=YEAR, month=MONTH)

    # 7) (Opcional) Bolsa de horas del mes (CSV fijos)
    if DO_HOURS_BAG_MONTH:
        controller.run_hours_bag_month(year=YEAR, month=MONTH, employee_ids=None)

    # 8) (Opcional) Prueba de un único empleado
    if DO_SINGLE_EMPLOYEE_WORK_ENTRIES:
        controller.run_get_work_entries_month(employee_id=EMPLOYEE_ID, year=YEAR, month=MONTH)

    # 9) Worked Hours (TODOS los empleados) para el rango 17–29/09/2025 inclusivo
    if DO_EXPORT_WORKED_HOURS_RANGE:
        controller.run_export_worked_hours_stats_range(
            date_from="2025-09-17",
            date_to="2025-09-29",
            with_checks=WITH_CHECKS,
        )

    # 10) NUEVO (mínima modificación): Ausencias y Vacaciones (empleado a empleado) mismo rango
    if DO_EXPORT_DAY_OFFS_RANGE:
        controller.run_export_day_offs_range(
            date_from="2025-09-17",
            date_to="2025-09-29",
        )
