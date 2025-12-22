# application/use_cases/daily_attendance_use_cases.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.application.use_cases.employee_use_cases import EmployeeUseCases
from sesame_connector.application.use_cases.worked_hours_use_cases import WorkedHoursUseCases
from sesame_connector.domain.models.employee import Employee
from sesame_connector.domain.models.work_entry import WorkEntry
from sesame_connector.domain.models.worked_hours_stat import WorkedHoursStat

SAFE_PAGE_SIZE = 200


@dataclass
class OpenEntryRow:
    employee_id: str
    employee_name: Optional[str]
    email: Optional[str]
    last_in_at: Optional[datetime]
    last_in_office_id: Optional[str]


@dataclass
class ClosedEntryRow:
    employee_id: str
    employee_name: Optional[str]
    email: Optional[str]
    in_at: Optional[datetime]
    out_at: Optional[datetime]
    in_office_id: Optional[str]
    out_office_id: Optional[str]
    seconds_worked: int
    seconds_to_work: Optional[int]
    seconds_diff: Optional[int]
    met_schedule: Optional[bool]
    missing_seconds: Optional[int]
    hours_worked: float
    hours_to_work: Optional[float]
    hours_missing: Optional[float]


@dataclass
class NoEntryRow:
    employee_id: str
    employee_name: Optional[str]
    email: Optional[str]


@dataclass
class DailyAttendanceSummary:
    date: str
    active_employees: int
    open_entries: List[OpenEntryRow]
    closed_entries: List[ClosedEntryRow]
    no_entries: List[NoEntryRow]
    closed_met_schedule_count: int
    closed_not_met_schedule_count: int


class DailyAttendanceUseCases:
    """
    Use case de “asistencia diaria”.

    Responsabilidades:
      - Obtener fichajes cerrados por empleado en una fecha.
      - Obtener horas trabajadas por empleado en una fecha.
      - Obtener horas teóricas por empleado en una fecha.
      - Construir un resumen por empleado (cumple horario / le faltan horas).
    """

    def __init__(self, repo: SesamePort, emp_uc: EmployeeUseCases, wh_uc: WorkedHoursUseCases) -> None:
        self._repo = repo
        self._emp_uc = emp_uc
        self._wh_uc = wh_uc

    # ───────────────── Helpers internos ─────────────────

    @staticmethod
    def _normalize_date(date_str: Optional[str]) -> str:
        if date_str:
            # Validamos formato; si es incorrecto lanzará ValueError.
            _ = date.fromisoformat(date_str)
            return date_str
        return date.today().isoformat()

    def _active_employees(self, employee_ids: Optional[List[str]] = None) -> List[Employee]:
        """
        Devuelve la lista de empleados activos.
        Si `employee_ids` viene informado y no está vacío,
        se filtra para devolver sólo esos ids.
        """
        employees = self._emp_uc.list_employees(only_active=True, page_size=SAFE_PAGE_SIZE)

        if not employee_ids:
            # None o lista vacía → todos los activos
            return employees

        allowed = set(employee_ids)
        return [e for e in employees if e.id in allowed]

    @staticmethod
    def _is_work_entry(entry: WorkEntry) -> bool:
        """
        Devuelve True si el fichaje se considera de trabajo (no descanso, etc.).

        Criterio:
          - Si work_entry_type es None → lo consideramos trabajo (compatibilidad).
          - Si viene informado, sólo consideramos trabajo cuando sea 'work' (case-insensitive).
        """
        t = (entry.work_entry_type or "").strip().lower()
        if not t:
            # Datos antiguos o API que no informa el tipo → asumimos trabajo
            return True
        return t == "work"


    # ───────────────── 1) Fichajes cerrados ─────────────────

    def get_closed_work_entries_for_date(self, *, date_str: str) -> Dict[str, WorkEntry]:
        """
        Devuelve, para la fecha dada (YYYY-MM-DD), el ÚLTIMO fichaje CERRADO
        de TRABAJO por empleado activo: { employee_id -> WorkEntry }.
        """
        date_str = self._normalize_date(date_str)
        employees = self._active_employees()
        closed_by_emp: Dict[str, WorkEntry] = {}

        for emp in employees:
            if not emp.id:
                continue

            entries: List[WorkEntry] = []
            page = 1
            while True:
                chunk = self._repo.list_work_entries(
                    employee_id=emp.id,
                    date_from=date_str,
                    date_to=date_str,
                    page=page,
                    page_size=SAFE_PAGE_SIZE,
                )
                if not chunk:
                    break
                entries.extend(chunk)
                if len(chunk) < SAFE_PAGE_SIZE:
                    break
                page += 1

            # Nos quedamos solo con fichajes de trabajo
            work_entries = [we for we in entries if self._is_work_entry(we)]

            closed = [we for we in work_entries if we.in_at is not None and we.out_at is not None]
            if not closed:
                continue

            closed.sort(
                key=lambda we: (
                    we.in_at or datetime.min,
                    we.out_at or datetime.min,
                )
            )
            closed_by_emp[emp.id] = closed[-1]

        return closed_by_emp

    # ───────────────── 2) Horas trabajadas ─────────────────

    def get_worked_seconds_for_date(self, *, date_str: str) -> Dict[str, int]:
        """
        Devuelve { employee_id -> seconds_worked } para la fecha dada.
        (Usa /schedule/v1/reports/worked-hours).
        """
        date_str = self._normalize_date(date_str)
        stats = self._wh_uc.list_worked_hours_all_employees_range(
            date_from=date_str,
            date_to=date_str,
            with_checks=False,
        )
        return {s.employee_id: int(s.seconds_worked or 0) for s in stats if s.employee_id}

    # ───────────────── 3) Horas teóricas ─────────────────

    def get_theoretical_seconds_for_date(self, *, date_str: str) -> Dict[str, Optional[int]]:
        """
        Devuelve { employee_id -> seconds_to_work } para la fecha dada.
        (Misma API de worked-hours, pero usamos el campo seconds_to_work).
        """
        date_str = self._normalize_date(date_str)
        stats = self._wh_uc.list_worked_hours_all_employees_range(
            date_from=date_str,
            date_to=date_str,
            with_checks=False,
        )
        result: Dict[str, Optional[int]] = {}
        for s in stats:
            if not s.employee_id:
                continue
            result[s.employee_id] = int(s.seconds_to_work) if s.seconds_to_work is not None else None
        return result

    # ───────────────── 4) Orquestador: estado diario ─────────────────

    def build_status_for_date(
        self,
        *,
        date_str: str,
        employee_ids: Optional[List[str]] = None,
    ) -> DailyAttendanceSummary:
        """
        Orquesta:
          - fichajes abiertos/cerrados
          - horas trabajadas / teóricas
        y devuelve un resumen de asistencia por empleado.

        Si `employee_ids` viene informado:
          - Sólo procesa esos empleados (si están activos).
        Si es None o lista vacía:
          - Procesa todos los empleados activos.
        """
        date_str = self._normalize_date(date_str)
        employees = self._active_employees(employee_ids=employee_ids)

        # stats de horas (trabajadas + teóricas) en un solo viaje
        stats: List[WorkedHoursStat] = self._wh_uc.list_worked_hours_all_employees_range(
            date_from=date_str,
            date_to=date_str,
            with_checks=False,
        )
        stats_by_emp: Dict[str, WorkedHoursStat] = {
            s.employee_id: s for s in stats if s.employee_id
        }

        open_rows: List[OpenEntryRow] = []
        closed_rows: List[ClosedEntryRow] = []
        no_entries_rows: List[NoEntryRow] = []
        closed_met_schedule_count = 0
        closed_not_met_schedule_count = 0

        for emp in employees:
            if not emp.id:
                continue

            emp_name = " ".join(filter(None, [emp.first_name, emp.last_name])) or None

            # Fichajes del día por empleado
            entries: List[WorkEntry] = []
            page = 1
            while True:
                chunk = self._repo.list_work_entries(
                    employee_id=emp.id,
                    date_from=date_str,
                    date_to=date_str,
                    page=page,
                    page_size=SAFE_PAGE_SIZE,
                    order_by="workEntryIn.date asc",
                )
                if not chunk:
                    break
                entries.extend(chunk)
                if len(chunk) < SAFE_PAGE_SIZE:
                    break
                page += 1

            if not entries:
                no_entries_rows.append(
                    NoEntryRow(
                        employee_id=emp.id,
                        employee_name=emp_name,
                        email=emp.email,
                    )
                )
                continue

            # Sólo fichajes de TRABAJO (ignoramos descansos, etc.)
            work_entries: List[WorkEntry] = [
                we for we in entries if self._is_work_entry(we)
            ]

            if not work_entries:
                # Sólo tiene descansos u otros tipos → para nuestro reporte
                # es como si no tuviera fichajes de trabajo
                no_entries_rows.append(
                    NoEntryRow(
                        employee_id=emp.id,
                        employee_name=emp_name,
                        email=emp.email,
                    )
                )
                continue

            # Ordenamos sólo los fichajes de trabajo
            entries_sorted = sorted(
                work_entries,
                key=lambda we: (
                    we.in_at or datetime.min,
                    we.out_at or datetime.min,
                ),
            )
            last_work_entry = entries_sorted[-1]
            is_open = (
                    last_work_entry.in_at is not None
                    and last_work_entry.out_at is None
            )

            # última CERRADA de TRABAJO
            last_closed_entry: Optional[WorkEntry] = None
            for we in reversed(entries_sorted):
                if we.in_at is not None and we.out_at is not None:
                    last_closed_entry = we
                    break

            if is_open:
                # Tiene un fichaje de TRABAJO abierto ahora mismo → solo "open"
                open_rows.append(
                    OpenEntryRow(
                        employee_id=emp.id,
                        employee_name=emp_name,
                        email=emp.email,
                        last_in_at=last_work_entry.in_at,
                        last_in_office_id=last_work_entry.in_office_id,
                    )
                )

            elif last_closed_entry is not None:
                # NO está abierto y sí tiene al menos un fichaje de trabajo cerrado hoy
                stat = stats_by_emp.get(emp.id)
                seconds_worked = int(stat.seconds_worked or 0) if stat else 0
                seconds_to_work = (
                    int(stat.seconds_to_work)
                    if (stat and stat.seconds_to_work is not None)
                    else None
                )

                if seconds_to_work is not None and seconds_to_work > 0:
                    seconds_diff = seconds_worked - seconds_to_work
                    met_schedule = seconds_diff >= 0
                    missing_seconds = max(-seconds_diff, 0)
                else:
                    seconds_diff = None
                    met_schedule = None
                    missing_seconds = None

                hours_worked = round(seconds_worked / 3600.0, 2)
                hours_to_work = (
                    round(seconds_to_work / 3600.0, 2)
                    if seconds_to_work is not None
                    else None
                )
                hours_missing = (
                    round(missing_seconds / 3600.0, 2)
                    if missing_seconds is not None
                    else None
                )

                if met_schedule is True:
                    closed_met_schedule_count += 1
                elif met_schedule is False:
                    closed_not_met_schedule_count += 1

                closed_rows.append(
                    ClosedEntryRow(
                        employee_id=emp.id,
                        employee_name=emp_name,
                        email=emp.email,
                        in_at=last_closed_entry.in_at,
                        out_at=last_closed_entry.out_at,
                        in_office_id=last_closed_entry.in_office_id,
                        out_office_id=last_closed_entry.out_office_id,
                        seconds_worked=seconds_worked,
                        seconds_to_work=seconds_to_work,
                        seconds_diff=seconds_diff,
                        met_schedule=met_schedule,
                        missing_seconds=missing_seconds,
                        hours_worked=hours_worked,
                        hours_to_work=hours_to_work,
                        hours_missing=hours_missing,
                    )
                )

        return DailyAttendanceSummary(
            date=date_str,
            active_employees=len(employees),
            open_entries=open_rows,
            closed_entries=closed_rows,
            no_entries=no_entries_rows,
            closed_met_schedule_count=closed_met_schedule_count,
            closed_not_met_schedule_count=closed_not_met_schedule_count,
        )
