# infrastructure/filesystem/csv_repository.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict, Any

import pandas as pd

from domain.models.employee import Employee


class CsvRepository:
    """Escritura de CSVs en disco."""

    def __init__(self, output_dir: Path | str = "output") -> None:
        self.output_dir = Path(output_dir)

    def save_employees(self, employees: Iterable[Employee]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = [e.model_dump(mode="python") for e in employees]
        df = pd.DataFrame(rows)

        preferred_cols = [
            # Identificación
            "id", "status", "code", "pin",
            # Nombre y contacto
            "first_name", "last_name", "email", "personal_mail",
            "phone", "work_phone", "emergency_phone",
            # Empresa
            "company_id", "company_name", "company_notification_email",
            "company_language", "company_created_at", "company_updated_at",
            # Perfil
            "work_status", "image_profile_url", "gender", "language",
            # Dirección
            "address", "postal_code", "city", "province", "country",
            # Documentación y bancario
            "nid", "identity_number_type", "ssn", "account_number", "bic",
            # Laboral
            "contract_id", "job_charge_id", "job_charge_name",
            "price_per_hour", "salary_range", "professional_category_code",
            "professional_category_description", "study_level",
            # Fechas y datos personales
            "date_of_birth", "children", "disability", "nationality", "nationalities",
            "description", "nfc",
            # Recruiter principal
            "main_recruiter_id", "main_recruiter_first_name", "main_recruiter_last_name",
            "main_recruiter_email", "main_recruiter_work_status",
            "main_recruiter_work_check_type_color", "main_recruiter_work_check_type_name",
            # Timestamps
            "created_at", "updated_at",
        ]
        # Mantener orden: preferidos + el resto
        cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
        df = df[cols]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"employees_{ts}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path
