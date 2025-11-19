# application/use_cases/employee_use_cases.py
from __future__ import annotations

from typing import Iterable, List, Optional

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.employee import Employee


class EmployeeUseCases:
    """Orquestador de casos de uso sobre Empleados."""

    def __init__(self, sesame_repo: SesamePort) -> None:
        self._repo = sesame_repo

    def list_employees(self, *, only_active: Optional[bool] = None, page_size: int = 100) -> List[Employee]:
        page = 1
        result: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=only_active, page=page, page_size=page_size)
            if not chunk:
                break
            result.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
        return result

    def create_employee(self, employee: Employee) -> Employee:
        return self._repo.create_employee(employee)

    def bulk_create(self, employees: Iterable[Employee]) -> List[Employee]:
        return self._repo.bulk_create_employees(employees)
