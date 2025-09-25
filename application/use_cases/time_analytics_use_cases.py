# application/use_cases/time_analytics_use_cases.py
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from application.interfaces.sesame_port import SesamePort
from domain.models.work_entry import WorkEntry
from domain.models.hours_bag_history import HoursBagHistory


@dataclass
class EmployeeHours:
    employee_id: str
    employee_name: str
    employee_email: Optional[str]
    total_seconds: int


@dataclass
class OfficeHours:
    office_id: str
    total_seconds: int


@dataclass
class HoursBagTotals:
    employee_id: str
    employee_name: str
    seconds_sum: int
    check_seconds_sum: int
    check_seconds_with_variation_sum: int


class TimeAnalyticsUseCases:
    """Cálculos de horas a partir de /schedule/v1/work-entries y bolsa de horas."""

    def __init__(self, sesame_repo: SesamePort) -> None:
        self._repo = sesame_repo

    # -------- helpers --------
    @staticmethod
    def _parse_dt(dt: Optional[datetime | str]) -> Optional[datetime]:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt
        try:
            return datetime.fromisoformat(dt)
        except Exception:
            return None

    @classmethod
    def _seconds_for_entry(cls, e: WorkEntry) -> int:
        if e.worked_seconds is not None:
            try:
                return int(e.worked_seconds)
            except Exception:
                pass
        start = cls._parse_dt(e.in_at)
        end = cls._parse_dt(e.out_at)
        if start and end:
            delta = end - start
            return max(0, int(delta.total_seconds()))
        return 0

    @staticmethod
    def _month_bounds(year: int, month: int) -> Tuple[str, str]:
        last = calendar.monthrange(year, month)[1]
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"

    # -------- public API (work-entries) --------
    def get_company_work_entries_month(
        self, *, year: int, month: int, page_size: int = 1000
    ) -> List[WorkEntry]:
        date_from, date_to = self._month_bounds(year, month)
        return self._repo.list_work_entries(
            employee_id=None, date_from=date_from, date_to=date_to, page_size=page_size
        )

    def hours_by_employee(self, entries: Iterable[WorkEntry]) -> List[EmployeeHours]:
        totals: Dict[str, EmployeeHours] = {}
        for e in entries:
            emp_id = e.employee_id or "UNKNOWN"
            secs = self._seconds_for_entry(e)
            if emp_id not in totals:
                full_name = " ".join(filter(None, [e.employee_first_name, e.employee_last_name])).strip()
                totals[emp_id] = EmployeeHours(
                    employee_id=emp_id,
                    employee_name=full_name or emp_id,
                    employee_email=str(e.employee_email) if e.employee_email else None,
                    total_seconds=0,
                )
            totals[emp_id].total_seconds += secs
        return sorted(totals.values(), key=lambda x: x.total_seconds, reverse=True)

    def hours_by_office(self, entries: Iterable[WorkEntry]) -> List[OfficeHours]:
        totals: Dict[str, int] = {}
        for e in entries:
            secs = self._seconds_for_entry(e)
            office_ids = []
            if e.in_office_id:
                office_ids.append(e.in_office_id)
            if e.out_office_id and e.out_office_id != e.in_office_id:
                office_ids.append(e.out_office_id)
            if not office_ids:
                office_ids = ["UNKNOWN"]

            share = max(1, len(office_ids))
            for oid in office_ids:
                totals[oid] = totals.get(oid, 0) + int(secs / share)

        result = [OfficeHours(office_id=k, total_seconds=v) for k, v in totals.items()]
        return sorted(result, key=lambda x: x.total_seconds, reverse=True)

    def coordinates_rows(self, entries: Iterable[WorkEntry]) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for e in entries:
            rows.append(
                {
                    "id": e.id,
                    "employee_id": e.employee_id,
                    "employee_name": " ".join(filter(None, [e.employee_first_name, e.employee_last_name])) or "",
                    "in_at": e.in_at,
                    "in_latitude": e.in_latitude,
                    "in_longitude": e.in_longitude,
                    "in_office_id": e.in_office_id,
                    "out_at": e.out_at,
                    "out_latitude": e.out_latitude,
                    "out_longitude": e.out_longitude,
                    "out_office_id": e.out_office_id,
                }
            )
        return rows

    # -------- public API (hours-bag) --------
    def get_hours_bag_month(
        self,
        *,
        year: int,
        month: int,
        employee_ids: Optional[List[str]] = None,
        page_size: int = 1000,
    ) -> List[HoursBagHistory]:
        date_from, date_to = self._month_bounds(year, month)
        return self._repo.list_hours_bag_rule_history(
            date_from=date_from,
            date_to=date_to,
            employee_ids=employee_ids,
            hours_bag_rule_ids=None,
            page=1,
            page_size=page_size,
        )

    @staticmethod
    def hours_bag_totals_by_employee(items: Iterable[HoursBagHistory]) -> List[HoursBagTotals]:
        agg: Dict[str, HoursBagTotals] = {}
        for it in items:
            eid = it.employee_id or "UNKNOWN"
            if eid not in agg:
                agg[eid] = HoursBagTotals(
                    employee_id=eid,
                    employee_name=it.employee_name or eid,
                    seconds_sum=0,
                    check_seconds_sum=0,
                    check_seconds_with_variation_sum=0,
                )
            agg[eid].seconds_sum += int(it.seconds or 0)
            agg[eid].check_seconds_sum += int(it.check_seconds or 0)
            agg[eid].check_seconds_with_variation_sum += int(it.check_seconds_with_variation or 0)
        return sorted(
            agg.values(),
            key=lambda x: x.check_seconds_with_variation_sum or x.check_seconds_sum,
            reverse=True,
        )
