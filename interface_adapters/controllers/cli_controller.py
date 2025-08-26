# interface_adapters/controllers/cli_controller.py
from __future__ import annotations

import logging
from typing import List

from application.use_cases.employee_use_cases import EmployeeUseCases
from application.use_cases.security_use_cases import SecurityUseCases
from domain.models.employee import Employee
from infrastructure.filesystem.csv_repository import CsvRepository


class CLIController:
    """Controlador simple para demo en local (listar y exportar empleados)."""

    def __init__(self, employee_uc: EmployeeUseCases, security_uc: SecurityUseCases) -> None:
        self._emp = employee_uc
        self._sec = security_uc
        self._logger = logging.getLogger(self.__class__.__name__)

    def run_demo(self, *, create_demo: bool = False) -> None:
        # 1) Verificar token/compañía
        info = self._sec.show_token_info()
        self._logger.info("Token verificado. Company id=%s name=%s", info.company.id, info.company.name)

        # 2) Listar empleados activos (paginando desde el UC)
        self._logger.info("=== Listar empleados (activos) ===")
        employees: List[Employee] = self._emp.list_employees(only_active=True, page_size=200)
        self._logger.info("Empleados activos: %s", len(employees))

        # Mostrar un pequeño preview
        for e in employees[:5]:
            correo = e.email or e.personal_mail or "sin email"
            self._logger.info(" - %s %s (%s)", e.first_name, e.last_name, correo)

        # 3) Exportar a CSV en ./output
        path = CsvRepository(output_dir="output").save_employees(employees)
        self._logger.info("CSV generado en: %s", path)

        # 4) (Opcional) crear empleado de demo — desactivado por ahora para centrar la exportación
        if create_demo:
            self._logger.info("Creación de demo desactivada por ahora.")
