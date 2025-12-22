# sesame_connector/domain/models/work_entry.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import EmailStr, Field

from sesame_connector.domain.models.base import DomainModel


class WorkEntry(DomainModel):
    id: str = Field(...)

    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[EmailStr] = None

    work_entry_type: Optional[str] = None
    work_check_type_id: Optional[str] = None

    in_at: Optional[datetime] = None
    out_at: Optional[datetime] = None

    in_latitude: Optional[float] = None
    in_longitude: Optional[float] = None
    out_latitude: Optional[float] = None
    out_longitude: Optional[float] = None

    in_office_id: Optional[str] = None
    out_office_id: Optional[str] = None

    worked_seconds: Optional[int] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    raw: Optional[Dict[str, Any]] = None

    @property
    def employee_display_name(self) -> str:
        return " ".join([x for x in [self.employee_first_name, self.employee_last_name] if x]).strip()

    @property
    def is_open(self) -> bool:
        return self.in_at is not None and self.out_at is None
