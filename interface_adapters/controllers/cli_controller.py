# interface_adapters/controllers/cli_controller.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from application.use_cases.employee_use_cases import EmployeeUseCases
from application.use_cases.security_use_cases import SecurityUseCases
from domain.models.employee import Employee
from domain.models.work_entry import WorkEntry
from domain.models.time_entry import TimeEntry
from domain.models.hours_bag_history import HoursBagHistory
from domain.models.office import Office
from domain.models.employee_office_assignation import EmployeeOfficeAssignation
from infrastructure.filesystem.csv_repository import CsvRepository
from infrastructure.repositories.sesame_repository import SesameRepositoryImpl


class CLIController:
    def __init__(
        self,
        repo: SesameRepositoryImpl,
        csv_repo: CsvRepository,
        sec_uc: SecurityUseCases,
        emp_uc: EmployeeUseCases,
    ) -> None:
        self._repo = repo
        self._csv = csv_repo
        self._sec = sec_uc
        self._emp = emp_uc
        self._log = logging.getLogger(self.__class__.__name__)

    # ─────────────────────────────────────────────────────────────
    # Utilidades
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _month_bounds(year: int, month: int) -> Tuple[str, str]:
        first = date(year, month, 1)
        if month == 12:
            last = date(year + 1, 1, 1).replace(day=1)
        else:
            last = date(year, month + 1, 1)
        return (first.isoformat(), (last.replace(day=1)).isoformat())

    @staticmethod
    def _month_bounds_inclusive(year: int, month: int) -> Tuple[str, str]:
        """Devolver [from, to] inclusivo con el último día del mes."""
        first = date(year, month, 1)
        if month == 12:
            first_next = date(year + 1, 1, 1)
        else:
            first_next = date(year, month + 1, 1)
        last_day = (first_next - timedelta(days=1))
        return (first.isoformat(), last_day.isoformat())

    # ─────────────────────────────────────────────────────────────
    # 1) Token smoketest
    # ─────────────────────────────────────────────────────────────
    def run_token_info_smoketest(self) -> None:
        info = self._repo.get_token_info()
        company = info.get("parsed_company") or {}
        self._log.info(
            "Parsed company: %s (%s)", company.get("name") or "?", company.get("id") or "?"
        )
        out_path = Path("output") / "token_info_smoketest.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        self._log.info("Token smoketest guardado en: %s", str(out_path))

    # ─────────────────────────────────────────────────────────────
    # 2) Export empleados
    # ─────────────────────────────────────────────────────────────
    def run_export_employees(self) -> None:
        company = self._repo.get_company()
        self._log.info("Company: %s (%s)", company.get("name"), company.get("id"))

        # Paginación básica
        page = 1
        page_size = 100
        all_emps: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=True, page=page, page_size=page_size)
            all_emps.extend(chunk)
            if len(chunk) < min(page_size, 100):
                break
            page += 1

        path = self._csv.save_employees(all_emps)
        self._log.info("CSV empleados: %s", path)

    # ─────────────────────────────────────────────────────────────
    # 3) Export offices
    # ─────────────────────────────────────────────────────────────
    def run_export_offices(self) -> None:
        self._log.info("GET Offices (listar centros de trabajo)")
        # Paginación
        page, page_size = 1, 100
        offices: List[Office] = []
        while True:
            chunk = self._repo.list_offices(page=page, page_size=page_size)
            offices.extend(chunk)
            if len(chunk) < min(page_size, 100):
                break
            page += 1

        self._log.info("Centros de trabajo: %d", len(offices))
        path = self._csv.save_offices(offices)
        self._log.info("CSV offices: %s", path)

    # ─────────────────────────────────────────────────────────────
    # 4) NUEVO: Export employee–office assignations (todos)
    # ─────────────────────────────────────────────────────────────
    def run_export_employee_office_assignations_all(self) -> None:
        self._log.info("GET Employee–Office assignations (todos los empleados)")

        # 1) empleados (activos)
        page, page_size = 1, 100
        employees: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=True, page=page, page_size=page_size)
            employees.extend(chunk)
            if len(chunk) < min(page_size, 100):
                break
            page += 1

        # 2) por empleado, paginado
        assignations: List[EmployeeOfficeAssignation] = []
        for e in employees:
            apage = 1
            while True:
                achunk = self._repo.list_employee_office_assignations(
                    employee_id=e.id, page=apage, page_size=100
                )
                assignations.extend(achunk)
                if len(achunk) < 100:
                    break
                apage += 1

        path = self._csv.save_employee_office_assignations(assignations)
        self._log.info("CSV employee_office_assignations: %s", path)

    # ─────────────────────────────────────────────────────────────
    # 5) Work entries de TODOS los empleados (mes)
    # ─────────────────────────────────────────────────────────────
    def run_export_work_entries_all_month(self, *, year: int, month: int) -> None:
        company = self._repo.get_company()
        self._log.info("Company: %s (%s)", company.get("name"), company.get("id"))

        # Empleados activos
        page, page_size = 1, 100
        employees: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=True, page=page, page_size=page_size)
            employees.extend(chunk)
            if len(chunk) < min(page_size, 100):
                break
            page += 1

        date_from = date(year, month, 1).isoformat()
        if month == 12:
            date_to = date(year + 1, 1, 1).isoformat()
        else:
            date_to = date(year, month + 1, 1).isoformat()

        # Work entries por empleado
        all_entries: List[WorkEntry] = []
        for e in employees:
            wpage = 1
            while True:
                chunk = self._repo.list_work_entries(
                    employee_id=e.id,
                    date_from=date_from,
                    date_to=date_to,
                    page=wpage,
                    page_size=100,
                    order_by="workEntryIn.date asc",
                )
                all_entries.extend(chunk)
                if len(chunk) < 100:
                    break
                wpage += 1

        self._log.info("Work entries mes %04d-%02d (todos): %d", year, month, len(all_entries))
        path = self._csv.save_work_entries(all_entries, year=year, month=month, filename_prefix="work_entries")
        self._log.info("CSV work entries (todos): %s", path)

    # ─────────────────────────────────────────────────────────────
    # 6) Agregados: coordinates / hours_by_employee / hours_by_office
    # ─────────────────────────────────────────────────────────────
    def run_company_hours_report_month(self, *, year: int, month: int) -> None:
        # Cargamos work entries del CSV ya generado o hacemos llamada directa.
        # Para garantizar consistencia, volvemos a consultar (podrías leer CSV si prefieres).
        date_from = date(year, month, 1).isoformat()
        if month == 12:
            date_to = date(year + 1, 1, 1).isoformat()
        else:
            date_to = date(year, month + 1, 1).isoformat()

        # Empleados
        page, page_size = 1, 100
        employees: List[Employee] = []
        while True:
            chunk = self._repo.list_employees(only_active=True, page=page, page_size=page_size)
            employees.extend(chunk)
            if len(chunk) < min(page_size, 100):
                break
            page += 1

        # Work entries por empleado
        all_entries: List[WorkEntry] = []
        for e in employees:
            wpage = 1
            while True:
                chunk = self._repo.list_work_entries(
                    employee_id=e.id,
                    date_from=date_from,
                    date_to=date_to,
                    page=wpage,
                    page_size=100,
                    order_by="workEntryIn.date asc",
                )
                all_entries.extend(chunk)
                if len(chunk) < 100:
                    break
                wpage += 1

        # Coordinates
        coord_rows: List[Dict[str, object]] = []
        for we in all_entries:
            coord_rows.append(
                {
                    "work_entry_id": we.id,
                    "employee_id": we.employee_id,
                    "employee_name": " ".join([x for x in [we.employee_first_name, we.employee_last_name] if x]),
                    "in_at": we.in_at or "",
                    "in_latitude": we.in_latitude or "",
                    "in_longitude": we.in_longitude or "",
                    "out_at": we.out_at or "",
                    "out_latitude": we.out_latitude or "",
                    "out_longitude": we.out_longitude or "",
                    "in_office_id": we.in_office_id or "",
                    "out_office_id": we.out_office_id or "",
                }
            )
        coord_path = self._csv.save_coordinates(coord_rows, year=year, month=month)
        self._log.info("CSV coordenadas:        %s", coord_path)

        # Hours by employee
        sec_by_emp: Dict[str, int] = {}
        meta_emp: Dict[str, Tuple[str, str]] = {}
        for we in all_entries:
            if not we.employee_id:
                continue
            sec = int(we.worked_seconds or 0)
            sec_by_emp[we.employee_id] = sec_by_emp.get(we.employee_id, 0) + sec
            if we.employee_id not in meta_emp:
                meta_emp[we.employee_id] = (
                    " ".join([x for x in [we.employee_first_name, we.employee_last_name] if x]),
                    we.employee_email or "",
                )
        hours_by_emp_rows: List[Dict[str, object]] = []
        for emp_id, total_sec in sec_by_emp.items():
            emp_name, emp_email = meta_emp.get(emp_id, ("", ""))
            hours_by_emp_rows.append(
                {
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "employee_email": emp_email,
                    "total_seconds": total_sec,
                    "total_hours": round(total_sec / 3600, 2),
                }
            )
        path_emp = self._csv.save_hours_by_employee(hours_by_emp_rows, year=year, month=month)
        self._log.info("CSV horas por empleado: %s", path_emp)

        # Hours by office (sumar in_office_id / out_office_id si aplica; aquí sumamos por in_office_id)
        sec_by_off: Dict[str, int] = {}
        for we in all_entries:
            oid = we.in_office_id or "UNKNOWN"
            sec_by_off[oid] = sec_by_off.get(oid, 0) + int(we.worked_seconds or 0)
        hours_by_off_rows = [
            {"office_id": oid, "total_seconds": sec, "total_hours": round(sec / 3600, 2)}
            for oid, sec in sec_by_off.items()
        ]
        path_off = self._csv.save_hours_by_office(hours_by_off_rows, year=year, month=month)
        self._log.info("CSV horas por centro:   %s", path_off)

    # ─────────────────────────────────────────────────────────────
    # 7) GET Work entries (un empleado) – útil para pruebas
    # ─────────────────────────────────────────────────────────────
    def run_get_work_entries_month(self, *, employee_id: str, year: int, month: int) -> None:
        date_from = date(year, month, 1).isoformat()
        if month == 12:
            date_to = date(year + 1, 1, 1).isoformat()
        else:
            date_to = date(year, month + 1, 1).isoformat()

        self._log.info(
            "GET Work Entries mes completo: %s → %s  employee_id=%s",
            date_from,
            date_to,
            employee_id,
        )
        entries: List[WorkEntry] = []
        page = 1
        while True:
            chunk = self._repo.list_work_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=100,
                order_by="workEntryIn.date asc",
            )
            entries.extend(chunk)
            if len(chunk) < 100:
                break
            page += 1

        self._log.info("Total work entries en el mes: %d", len(entries))
        for e in entries:
            self._log.info(
                " - id=%s  in=%s  out=%s  type=%s",
                e.id,
                e.in_at,
                e.out_at,
                e.work_entry_type,
            )
        path = self._csv.save_work_entries(entries, year=year, month=month, filename_prefix="work_entries")
        self._log.info("CSV (mes %d/%d): %s", month, year, path)
