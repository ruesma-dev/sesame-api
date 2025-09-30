# domain/models/absence_day_off.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class AbsenceDayOff(BaseModel):
    id: str
    date: date
    seconds: Optional[int] = None

    # Calendar
    calendar_id: Optional[str] = None
    calendar_year: Optional[int] = None
    calendar_max_days_off: Optional[int] = None
    calendar_created_at: Optional[datetime] = None
    calendar_updated_at: Optional[datetime] = None

    # Absence Type
    absence_type_id: Optional[str] = None
    absence_type_name: Optional[str] = None
    absence_type_needs_validation: Optional[bool] = None
    absence_type_created_at: Optional[datetime] = None
    absence_type_updated_at: Optional[datetime] = None
    absence_type_created_by: Optional[str] = None

    # Employee (resumen)
    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[str] = None

    raw: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
