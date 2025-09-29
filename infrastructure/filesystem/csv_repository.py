# infrastructure/filesystem/csv_repository.py
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from domain.models.employee import Employee
from domain.models.work_entry import WorkEntry
from domain.models.time_entry import TimeEntry
from domain.models.office import Office
from domain.models.employee_office_assignation import EmployeeOfficeAssignation


class CsvRepository:
    def __init__(self, *, output_dir: str = "output") -> None:
        self._out = Path(output_dir)
        self._out.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────
    # Empleados
    # ─────────────────────────────────────────────────────────────
    def save_employees(self, employees: Sequence[Employee]) -> str:
        path = self._out / "employees.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "first_name", "last_name", "email", "status"])
            for e in employees:
                w.writerow([e.id, e.first_name, e.last_name, (e.email or ""), (e.status or "")])
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Offices
    # ─────────────────────────────────────────────────────────────
    def save_offices(self, offices: Sequence[Office]) -> str:
        path = self._out / "offices.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "id",
                    "name",
                    "address",
                    "latitude",
                    "longitude",
                    "description",
                    "radius",
                    "default_timezone",
                    "created_at",
                    "updated_at",
                ]
            )
            for o in offices:
                w.writerow(
                    [
                        o.id,
                        o.name or "",
                        o.address or "",
                        o.latitude or "",
                        o.longitude or "",
                        o.description or "",
                        o.radius or "",
                        o.default_timezone or "",
                        o.created_at or "",
                        o.updated_at or "",
                    ]
                )
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Employee–Office assignations
    # ─────────────────────────────────────────────────────────────
    def save_employee_office_assignations(self, items: Sequence[EmployeeOfficeAssignation]) -> str:
        path = self._out / "employee_office_assignations.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "assignation_id",
                    "employee_id",
                    "employee_name",
                    "employee_email",
                    "office_id",
                    "office_name",
                    "office_address",
                    "office_latitude",
                    "office_longitude",
                    "office_description",
                    "office_radius",
                    "default_timezone",
                    "created_at",
                    "updated_at",
                ]
            )
            for a in items:
                w.writerow(
                    [
                        a.id,
                        a.employee_id or "",
                        " ".join([x for x in [a.employee_first_name, a.employee_last_name] if x]),
                        a.employee_email or "",
                        a.office_id or "",
                        a.office_name or "",
                        a.office_address or "",
                        a.office_latitude or "",
                        a.office_longitude or "",
                        a.office_description or "",
                        a.office_radius or "",
                        # FIX: el campo correcto en el modelo es office_default_timezone
                        a.office_default_timezone or "",
                        a.created_at or "",
                        a.updated_at or "",
                    ]
                )
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Work Entries (raw)
    # ─────────────────────────────────────────────────────────────
    def save_work_entries(
        self,
        entries: Sequence[WorkEntry],
        *,
        year: int | None = None,
        month: int | None = None,
        filename_prefix: str = "work_entries",
    ) -> str:
        path = self._out / f"{filename_prefix}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "id",
                    "employee_id",
                    "employee_name",
                    "employee_email",
                    "in_at",
                    "in_latitude",
                    "in_longitude",
                    "out_at",
                    "out_latitude",
                    "out_longitude",
                    "in_office_id",
                    "out_office_id",
                    "work_entry_type",
                    "worked_seconds",
                ]
            )
            for e in entries:
                w.writerow(
                    [
                        e.id,
                        e.employee_id,
                        " ".join([x for x in [e.employee_first_name, e.employee_last_name] if x]),
                        e.employee_email,
                        e.in_at or "",
                        e.in_latitude or "",
                        e.in_longitude or "",
                        e.out_at or "",
                        e.out_latitude or "",
                        e.out_longitude or "",
                        e.in_office_id or "",
                        e.out_office_id or "",
                        e.work_entry_type or "",
                        e.worked_seconds or 0,
                    ]
                )
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Time Entries (raw)
    # ─────────────────────────────────────────────────────────────
    def save_time_entries(
        self,
        entries: Sequence[TimeEntry],
        *,
        year: int | None = None,
        month: int | None = None,
        filename_prefix: str = "time_entries",
    ) -> str:
        path = self._out / f"{filename_prefix}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "id",
                    "employee_id",
                    "employee_name",
                    "employee_email",
                    "project_id",
                    "tag_ids",
                    "in_at",
                    "in_latitude",
                    "in_longitude",
                    "out_at",
                    "out_latitude",
                    "out_longitude",
                    "comment",
                ]
            )
            for t in entries:
                w.writerow(
                    [
                        t.id,
                        t.employee_id,
                        " ".join([x for x in [t.employee_first_name, t.employee_last_name] if x]),
                        t.employee_email,
                        t.project_id or "",
                        ";".join(t.tag_ids or []) if isinstance(t.tag_ids, list) else (t.tag_ids or ""),
                        t.in_at or "",
                        t.in_latitude or "",
                        t.in_longitude or "",
                        t.out_at or "",
                        t.out_latitude or "",
                        t.out_longitude or "",
                        t.comment or "",
                    ]
                )
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Agregados
    # ─────────────────────────────────────────────────────────────
    def save_hours_by_employee(self, rows: Iterable[Mapping[str, object]], *, year: int, month: int) -> str:
        path = self._out / "hours_by_employee.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["employee_id", "employee_name", "employee_email", "total_seconds", "total_hours"],
            )
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return str(path)

    def save_hours_by_office(self, rows: Iterable[Mapping[str, object]], *, year: int, month: int) -> str:
        path = self._out / "hours_by_office.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["office_id", "total_seconds", "total_hours"])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return str(path)

    def save_coordinates(self, rows: Iterable[Mapping[str, object]], *, year: int, month: int) -> str:
        path = self._out / "coordinates.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "work_entry_id",
                    "employee_id",
                    "employee_name",
                    "in_at",
                    "in_latitude",
                    "in_longitude",
                    "out_at",
                    "out_latitude",
                    "out_longitude",
                    "in_office_id",
                    "out_office_id",
                ],
            )
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Bolsa de horas
    # ─────────────────────────────────────────────────────────────
    def save_hours_bag_history(self, rows: Iterable[Mapping[str, object]], *, year: int, month: int) -> str:
        path = self._out / "hours_bag_history.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "date",
                    "employee_id",
                    "employee_name",
                    "hours_bag_rule_id",
                    "hours_bag_rule_name",
                    "hours_bag_rule_variation",
                    "seconds",
                    "check_seconds",
                    "check_seconds_with_variation",
                ],
            )
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return str(path)

    def save_hours_bag_totals_by_employee(self, rows: Iterable[Mapping[str, object]], *, year: int, month: int) -> str:
        path = self._out / "hours_bag_totals_by_employee.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "employee_id",
                    "employee_name",
                    "seconds_sum",
                    "check_seconds_sum",
                    "check_seconds_with_variation_sum",
                    "hours_sum",
                    "check_hours_sum",
                    "check_hours_with_variation_sum",
                ],
            )
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return str(path)
