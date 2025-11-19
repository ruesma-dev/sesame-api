# application/use_cases/office_use_cases.py
from __future__ import annotations

from typing import Dict, List

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.employee_office_assignation import EmployeeOfficeAssignation


SAFE_PAGE_SIZE = 200


class OfficeUseCases:
    """Casos de uso relacionados con centros de trabajo por empleado."""

    def __init__(self, repo: SesamePort) -> None:
        self._repo = repo

    def list_assignations_for_employee(self, employee_id: str) -> List[EmployeeOfficeAssignation]:
        page = 1
        out: List[EmployeeOfficeAssignation] = []
        while True:
            chunk = self._repo.list_employee_office_assignations(
                employee_id=employee_id,
                page=page,
                page_size=SAFE_PAGE_SIZE,
            )
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < SAFE_PAGE_SIZE:
                break
            page += 1
        return out

    def list_assignations_for_all_active_employees(self) -> List[EmployeeOfficeAssignation]:
        # Traemos todos los empleados activos y consultamos por empleado para evitar límites globales.
        employees = self._repo.list_employees(only_active=True, page=1, page_size=SAFE_PAGE_SIZE)
        acc: List[EmployeeOfficeAssignation] = []
        for e in employees:
            acc.extend(self.list_assignations_for_employee(e.id))
        return acc

    @staticmethod
    def to_csv_rows(items: List[EmployeeOfficeAssignation]) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for it in items:
            rows.append(
                {
                    "assignation_id": it.id,
                    "employee_id": it.employee_id,
                    "employee_name": " ".join(filter(None, [it.employee_first_name, it.employee_last_name])) or None,
                    "employee_email": it.employee_email,
                    "office_id": it.office_id,
                    "office_name": it.office_name,
                    "office_address": it.office_address,
                    "office_latitude": it.office_latitude,
                    "office_longitude": it.office_longitude,
                    "office_description": it.office_description,
                    "office_radius": it.office_radius,
                    "office_default_timezone": it.office_default_timezone,
                    "created_at": it.created_at,
                    "updated_at": it.updated_at,
                }
            )
        return rows
