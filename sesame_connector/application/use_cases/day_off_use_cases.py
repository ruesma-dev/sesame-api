# application/use_cases/day_off_use_cases.py
from __future__ import annotations

from typing import List

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.employee import Employee
from sesame_connector.domain.models.absence_day_off import AbsenceDayOff
from sesame_connector.domain.models.vacation_day_off import VacationDayOff

SAFE_PAGE_SIZE = 200


class DayOffUseCases:
    """Orquestador de Ausencias y Vacaciones, empleado a empleado (sin bulk)."""

    def __init__(self, repo: SesamePort) -> None:
        self._repo = repo

    # Utilidad
    def _all_active_employees(self) -> List[Employee]:
        page, size = 1, SAFE_PAGE_SIZE
        out: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=True, page=page, page_size=size)
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < size:
                break
            page += 1
        return out

    # Ausencias
    def list_absences_all_employees_range(self, *, date_from: str, date_to: str) -> List[AbsenceDayOff]:
        emps = self._all_active_employees()
        out: List[AbsenceDayOff] = []
        for e in emps:
            if not e.id:
                continue
            page = 1
            while True:
                items, meta = self._repo.list_absence_day_off(
                    employee_ids=[e.id],
                    date_from=date_from,
                    date_to=date_to,
                    order_by="date asc",
                    page=page,
                    page_size=SAFE_PAGE_SIZE,
                )
                if not items:
                    break
                out.extend(items)
                current = int((meta or {}).get("currentPage") or page)
                last_page = int((meta or {}).get("lastPage") or current)
                if current >= last_page:
                    break
                page += 1
        return out

    # Vacaciones
    def list_vacations_all_employees_range(self, *, date_from: str, date_to: str) -> List[VacationDayOff]:
        emps = self._all_active_employees()
        out: List[VacationDayOff] = []
        for e in emps:
            if not e.id:
                continue
            page = 1
            while True:
                items, meta = self._repo.list_vacation_day_off(
                    employee_ids=[e.id],
                    date_from=date_from,
                    date_to=date_to,
                    order_by="date asc",
                    page=page,
                    page_size=SAFE_PAGE_SIZE,
                )
                if not items:
                    break
                out.extend(items)
                current = int((meta or {}).get("currentPage") or page)
                last_page = int((meta or {}).get("lastPage") or current)
                if current >= last_page:
                    break
                page += 1
        return out
