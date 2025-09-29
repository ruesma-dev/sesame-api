# application/use_cases/time_analytics_use_cases.py
from __future__ import annotations

import calendar
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from application.interfaces.sesame_port import SesamePort
from domain.models.employee import Employee
from domain.models.work_entry import WorkEntry
from domain.models.hours_bag_history import HoursBagHistory


SAFE_PAGE_SIZE = 200
BATCH_EMPLOYEE_IDS = 20


@dataclass
class HoursByEmployeeRow:
    employee_id: Optional[str]
    employee_name: Optional[str]
    employee_email: Optional[str]
    total_seconds: int


@dataclass
class HoursByOfficeRow:
    office_id: Optional[str]
    total_seconds: int


class TimeAnalyticsUseCases:
    def __init__(self, repo: SesamePort) -> None:
        self._repo = repo

    # ───────────────── Work Entries (todos los empleados, mes) ─────────────────
    def get_company_work_entries_month(self, *, year: int, month: int) -> List[WorkEntry]:
        last = calendar.monthrange(year, month)[1]
        date_from = f"{year:04d}-{month:02d}-01"
        date_to = f"{year:04d}-{month:02d}-{last:02d}"

        employees: List[Employee] = self._repo.list_employees(only_active=True, page=1, page_size=SAFE_PAGE_SIZE)
        entries: List[WorkEntry] = []

        for emp in employees:
            page = 1
            while True:
                chunk = self._repo.list_work_entries(
                    employee_id=emp.id, date_from=date_from, date_to=date_to, page=page, page_size=SAFE_PAGE_SIZE
                )
                if not chunk:
                    break
                entries.extend(chunk)
                if len(chunk) < SAFE_PAGE_SIZE:
                    break
                page += 1

        return entries

    def get_employee_work_entries_month(self, *, employee_id: str, year: int, month: int) -> List[WorkEntry]:
        last = calendar.monthrange(year, month)[1]
        date_from = f"{year:04d}-{month:02d}-01"
        date_to = f"{year:04d}-{month:02d}-{last:02d}"

        out: List[WorkEntry] = []
        page = 1
        while True:
            chunk = self._repo.list_work_entries(
                employee_id=employee_id, date_from=date_from, date_to=date_to, page=page, page_size=SAFE_PAGE_SIZE
            )
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < SAFE_PAGE_SIZE:
                break
            page += 1
        return out

    # ───────────────── Agregaciones (work entries) ─────────────────
    @staticmethod
    def hours_by_employee(entries: Iterable[WorkEntry]) -> List[HoursByEmployeeRow]:
        acc: Dict[str, HoursByEmployeeRow] = {}
        for w in entries:
            key = w.employee_id or "unknown"
            if key not in acc:
                acc[key] = HoursByEmployeeRow(
                    employee_id=w.employee_id,
                    employee_name=" ".join(filter(None, [w.employee_first_name, w.employee_last_name])) or None,
                    employee_email=w.employee_email,
                    total_seconds=0,
                )
            acc[key].total_seconds += int(w.worked_seconds or 0)
        return list(acc.values())

    @staticmethod
    def hours_by_office(entries: Iterable[WorkEntry]) -> List[HoursByOfficeRow]:
        acc: Dict[str, HoursByOfficeRow] = {}
        for w in entries:
            key = (w.in_office_id or w.out_office_id or "unknown")
            if key not in acc:
                acc[key] = HoursByOfficeRow(office_id=key if key != "unknown" else None, total_seconds=0)
            acc[key].total_seconds += int(w.worked_seconds or 0)
        return list(acc.values())

    @staticmethod
    def coordinates_rows(entries: Iterable[WorkEntry]) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for w in entries:
            rows.append(
                {
                    "work_entry_id": w.id,
                    "employee_id": w.employee_id,
                    "employee_name": " ".join(filter(None, [w.employee_first_name, w.employee_last_name])) or None,
                    "in_at": w.in_at,
                    "in_latitude": w.in_latitude,
                    "in_longitude": w.in_longitude,
                    "out_at": w.out_at,
                    "out_latitude": w.out_latitude,
                    "out_longitude": w.out_longitude,
                    "in_office_id": w.in_office_id,
                    "out_office_id": w.out_office_id,
                }
            )
        return rows

    # ───────────────── Bolsa de horas ─────────────────
    def get_hours_bag_month(
        self,
        *,
        year: int,
        month: int,
        employee_ids: Optional[List[str]] = None,
        hours_bag_rule_ids: Optional[List[str]] = None,
    ) -> List[HoursBagHistory]:
        last = calendar.monthrange(year, month)[1]
        date_from = f"{year:04d}-{month:02d}-01"
        date_to = f"{year:04d}-{month:02d}-{last:02d}"

        if employee_ids:
            ids = [x for x in employee_ids if x]
        else:
            employees = self._repo.list_employees(only_active=True, page=1, page_size=SAFE_PAGE_SIZE)
            ids = [e.id for e in employees if e.id]

        out: List[HoursBagHistory] = []

        def chunks(seq: List[str], size: int):
            for i in range(0, len(seq), size):
                yield seq[i:i + size]

        rule_ids = [r for r in (hours_bag_rule_ids or []) if r] or None

        for batch in chunks(ids, BATCH_EMPLOYEE_IDS):
            page = 1
            while True:
                chunk = self._repo.list_hours_bag_rule_history(
                    date_from=date_from,
                    date_to=date_to,
                    employee_ids=batch,
                    hours_bag_rule_ids=rule_ids,  # None ⇒ omitido
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

    @staticmethod
    def hours_bag_rows(items: Iterable[HoursBagHistory]) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for it in items:
            rows.append(
                {
                    "id": it.id,
                    "date": it.date,
                    "employee_id": it.employee_id,
                    "employee_name": it.employee_name,
                    "hours_bag_rule_id": it.hours_bag_rule_id,
                    "hours_bag_rule_name": it.hours_bag_rule_name,
                    "hours_bag_rule_variation": it.hours_bag_rule_variation,
                    "seconds": it.seconds,
                    "check_seconds": it.check_seconds,
                    "check_seconds_with_variation": it.check_seconds_with_variation,
                }
            )
        return rows

    @staticmethod
    def hours_bag_totals_by_employee(items: Iterable[HoursBagHistory]) -> List[Dict[str, object]]:
        """
        Agregado con las claves que espera CsvRepository.save_hours_bag_totals_by_employee:
          employee_id, employee_name,
          seconds_sum, check_seconds_sum, check_seconds_with_variation_sum,
          hours_sum, check_hours_sum, check_hours_with_variation_sum
        """
        acc: Dict[str, Dict[str, object]] = {}
        for it in items:
            key = it.employee_id or "unknown"
            row = acc.get(key)
            if row is None:
                row = {
                    "employee_id": it.employee_id,
                    "employee_name": it.employee_name,
                    "seconds_sum": 0,
                    "check_seconds_sum": 0,
                    "check_seconds_with_variation_sum": 0,
                    "hours_sum": 0.0,
                    "check_hours_sum": 0.0,
                    "check_hours_with_variation_sum": 0.0,
                }
                acc[key] = row
            row["seconds_sum"] = int(row["seconds_sum"]) + int(it.seconds or 0)
            row["check_seconds_sum"] = int(row["check_seconds_sum"]) + int(it.check_seconds or 0)
            row["check_seconds_with_variation_sum"] = int(row["check_seconds_with_variation_sum"]) + int(
                it.check_seconds_with_variation or 0
            )

        for row in acc.values():
            row["hours_sum"] = round(int(row["seconds_sum"]) / 3600.0, 2)
            row["check_hours_sum"] = round(int(row["check_seconds_sum"]) / 3600.0, 2)
            row["check_hours_with_variation_sum"] = round(int(row["check_seconds_with_variation_sum"]) / 3600.0, 2)

        return sorted(
            acc.values(),
            key=lambda r: ((r.get("employee_name") or "").lower(), (r.get("employee_id") or "")),
        )
