# application/use_cases/worked_hours_use_cases.py
from __future__ import annotations

import calendar
from typing import Dict, List

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.employee import Employee
from sesame_connector.domain.models.worked_hours_stat import WorkedHoursStat

SAFE_PAGE_SIZE = 200  # paginación segura por petición


class WorkedHoursUseCases:
    """Orquestador para /schedule/v1/reports/worked-hours (estadísticas por empleado)."""

    def __init__(self, repo: SesamePort) -> None:
        self._repo = repo

    def _iter_all_active_employees(self, page_size: int = SAFE_PAGE_SIZE) -> List[Employee]:
        page = 1
        out: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=True, page=page, page_size=page_size)
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
        return out

    def list_worked_hours_all_employees_range(
        self,
        *,
        date_from: str,  # "YYYY-MM-DD"
        date_to: str,    # "YYYY-MM-DD" (INCLUSIVO)
        with_checks: bool = False,
    ) -> List[WorkedHoursStat]:
        """
        Recolecta worked-hours para TODOS los empleados activos entre date_from y date_to (ambos inclusive),
        haciendo **UNA petición por empleado** (sin usar employeeIds[in] por lotes).
        """
        employees = self._iter_all_active_employees()
        out: List[WorkedHoursStat] = []

        for e in employees:
            if not e.id:
                continue

            page = 1
            while True:
                items, meta = self._repo.list_worked_hours_report(
                    employee_ids=[e.id],       # ← petición individual
                    date_from=date_from,
                    date_to=date_to,
                    with_checks=with_checks,
                    page=page,
                    page_size=SAFE_PAGE_SIZE,
                )

                # Si no hay items, salimos del bucle de este empleado
                if not items:
                    break

                out.extend(items)

                current = int((meta or {}).get("currentPage") or page)
                last_page = int((meta or {}).get("lastPage") or current)
                if current >= last_page:
                    break
                page += 1

        # SANITY: si la API devolviera duplicados por algún motivo, garantizamos unicidad por employee_id
        seen: Dict[str, WorkedHoursStat] = {}
        for it in out:
            if it.employee_id and it.employee_id not in seen:
                seen[it.employee_id] = it
        return list(seen.values())

    # Wrapper opcional por mes (compatibilidad)
    def list_worked_hours_all_employees_month(
        self,
        *,
        year: int,
        month: int,
        with_checks: bool = False,
    ) -> List[WorkedHoursStat]:
        last = calendar.monthrange(year, month)[1]
        return self.list_worked_hours_all_employees_range(
            date_from=f"{year:04d}-{month:02d}-01",
            date_to=f"{year:04d}-{month:02d}-{last:02d}",
            with_checks=with_checks,
        )
