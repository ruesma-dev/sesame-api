# sesame_connector/application/use_cases/employee_metrics_use_cases.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sesame_connector.application.use_cases.employee_use_cases import EmployeeUseCases
from sesame_connector.application.use_cases.day_off_use_cases import DayOffUseCases
from sesame_connector.application.use_cases.time_entries_use_cases import TimeEntriesUseCases
from sesame_connector.application.use_cases.worked_hours_use_cases import WorkedHoursUseCases


class EmployeeMetricsUseCases:
    """
    Orquestador de métricas por empleado / bloque.

    Objetivo:
      - extraer información en bloque o por subconjunto de empleados
      - componer datasets (worked_hours, vacaciones, ausencias, time_entries)
    """

    def __init__(
        self,
        *,
        employee_uc: Optional[EmployeeUseCases] = None,
        employees_uc: Optional[EmployeeUseCases] = None,  # alias tolerante
        worked_hours_uc: WorkedHoursUseCases,
        day_off_uc: DayOffUseCases,
        time_entries_uc: TimeEntriesUseCases,
    ) -> None:
        self._emp_uc = employee_uc or employees_uc
        if self._emp_uc is None:
            raise TypeError("Falta dependencia: employee_uc (o employees_uc)")

        self._wh_uc = worked_hours_uc
        self._dayoff_uc = day_off_uc
        self._te_uc = time_entries_uc

    def extract(
        self,
        *,
        date_from: str,
        date_to: str,
        employee_ids: Optional[List[str]] = None,
        only_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Devuelve un dict con datasets “listos para serializar” (Pydantic -> lo hace SesameClient).

        Nota:
        - employee_ids=None o [] => todos los empleados activos (si only_active=True)
        - si employee_ids viene informado => filtra a ese subconjunto (sobre la lista consultada)
        """
        employees = self._emp_uc.list_employees(only_active=only_active, page_size=200)

        if employee_ids:
            allowed = set(employee_ids)
            employees = [e for e in employees if e.id and e.id in allowed]

        scoped_employee_ids = [e.id for e in employees if e.id]

        # Worked hours (rango)
        worked_hours_items, worked_hours_meta = self._wh_uc.list_worked_hours(
            employee_ids=scoped_employee_ids or None,
            date_from=date_from,
            date_to=date_to,
            with_checks=False,
            all_pages=True,
        )

        # Day offs
        abs_items, abs_meta = self._dayoff_uc.list_absences(
            employee_ids=scoped_employee_ids or None,
            date_from=date_from,
            date_to=date_to,
            all_pages=True,
        )
        vac_items, vac_meta = self._dayoff_uc.list_vacations(
            employee_ids=scoped_employee_ids or None,
            date_from=date_from,
            date_to=date_to,
            all_pages=True,
        )

        # Time entries (tareas): si hay varios empleados, agregamos por empleado para no depender de si
        # el endpoint soporta “employeeId” múltiple (normalmente no).
        time_entries_all = []
        time_entries_meta: Dict[str, Any] = {"scope": "per_employee", "employee_count": len(scoped_employee_ids)}

        for emp_id in (scoped_employee_ids or []):
            items, meta = self._te_uc.list_time_entries(
                employee_id=emp_id,
                date_from=date_from,
                date_to=date_to,
                employee_status="active" if only_active else "inactive",
                all_pages=True,
                page_size=200,
            )
            time_entries_all.extend(items)

        time_entries_rows = self._te_uc.to_rows(time_entries_all)

        return {
            "scope": {
                "date_from": date_from,
                "date_to": date_to,
                "only_active": only_active,
                "employee_ids": scoped_employee_ids,
            },
            "employees": employees,
            "worked_hours": {"items": worked_hours_items, "meta": worked_hours_meta},
            "day_off": {
                "absences": {"items": abs_items, "meta": abs_meta},
                "vacations": {"items": vac_items, "meta": vac_meta},
            },
            "time_entries": {"items": time_entries_all, "rows": time_entries_rows, "meta": time_entries_meta},
        }
