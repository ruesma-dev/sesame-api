# infrastructure/filesystem/csv_repository.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict, Any

import pandas as pd

from domain.models.employee import Employee
from domain.models.time_entry import TimeEntry
from domain.models.work_entry import WorkEntry


class CsvRepository:
    """Escritura de CSVs en disco."""

    def __init__(self, output_dir: Path | str = "output") -> None:
        self.output_dir = Path(output_dir)

    # ---------- Employees ----------
    def save_employees(self, employees: Iterable[Employee]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = [e.model_dump(mode="python") for e in employees]
        df = pd.DataFrame(rows)
        preferred_cols = [
            "id", "status", "code", "pin",
            "first_name", "last_name", "email", "personal_mail",
            "phone", "work_phone",
            "company_id", "company_name", "company_notification_email",
            "company_language", "company_created_at", "company_updated_at",
            "work_status", "image_profile_url", "gender", "language",
            "address", "postal_code", "city", "province", "country",
            "nid", "identity_number_type", "ssn", "account_number", "bic",
            "contract_id", "job_charge_id", "job_charge_name",
            "price_per_hour", "salary_range",
            "professional_category_code", "professional_category_description",
            "study_level",
            "date_of_birth", "children", "disability", "nationality", "nationalities",
            "description", "nfc",
            "created_at", "updated_at",
        ]
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"employees_{ts}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    # ---------- Time entries ----------
    def save_time_entries(self, entries: Iterable[TimeEntry]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = [e.model_dump(mode="python") for e in entries]
        df = pd.DataFrame(rows)
        preferred_cols = [
            "id",
            "employee_id", "employee_first_name", "employee_last_name", "employee_email",
            "project_id", "tag_ids",
            "in_at", "in_latitude", "in_longitude",
            "out_at", "out_latitude", "out_longitude",
            "comment",
            "created_at", "updated_at", "deleted_at",
        ]
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"time_entries_{ts}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    # ---------- Work entries ----------
    def save_work_entries(self, entries: Iterable[WorkEntry]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = [e.model_dump(mode="python") for e in entries]
        df = pd.DataFrame(rows)
        preferred_cols = [
            "id", "work_check_type_id", "work_entry_type",
            "employee_id", "employee_first_name", "employee_last_name", "employee_email",
            "in_origin", "in_at", "in_latitude", "in_longitude", "in_office_id",
            "out_origin", "out_at", "out_latitude", "out_longitude", "out_office_id",
            "worked_seconds",
            "created_at", "updated_at", "deleted_at",
        ]
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"work_entries_{ts}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    # ---------- Agregados (work entries) ----------
    def save_hours_by_employee(self, rows: Iterable[Dict[str, Any]], *, year: int, month: int) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        preferred = ["employee_id", "employee_name", "employee_email", "total_seconds", "total_hours"]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]
        path = self.output_dir / f"hours_by_employee_{year:04d}{month:02d}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    def save_hours_by_office(self, rows: Iterable[Dict[str, Any]], *, year: int, month: int) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        preferred = ["office_id", "total_seconds", "total_hours"]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]
        path = self.output_dir / f"hours_by_office_{year:04d}{month:02d}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    def save_coordinates(self, rows: Iterable[Dict[str, Any]], *, year: int, month: int) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        preferred = [
            "id", "employee_id", "employee_name",
            "in_at", "in_latitude", "in_longitude", "in_office_id",
            "out_at", "out_latitude", "out_longitude", "out_office_id",
        ]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]
        path = self.output_dir / f"coordinates_{year:04d}{month:02d}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    # ---------- Bolsa de horas ----------
    def save_hours_bag_history(self, rows: Iterable[dict], *, year: int, month: int) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(list(rows))
        preferred = [
            "id", "date",
            "employee_id", "employee_name",
            "hours_bag_rule_id", "hours_bag_rule_name", "hours_bag_rule_variation",
            "seconds", "check_seconds", "check_seconds_with_variation",
        ]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]
        path = self.output_dir / f"hours_bag_history_{year:04d}{month:02d}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    def save_hours_bag_totals_by_employee(self, rows: Iterable[dict], *, year: int, month: int) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(list(rows))
        preferred = [
            "employee_id", "employee_name",
            "seconds_sum", "check_seconds_sum", "check_seconds_with_variation_sum",
            "hours_sum", "check_hours_sum", "check_hours_with_variation_sum",
        ]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]
        path = self.output_dir / f"hours_bag_totals_by_employee_{year:04d}{month:02d}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path
