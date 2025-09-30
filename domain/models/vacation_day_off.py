# domain/models/vacation_day_off.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class VacationDayOff(BaseModel):
    id: str
    date: date
    seconds: Optional[int] = None

    # Calendar
    calendar_id: Optional[str] = None
    calendar_year: Optional[int] = None
    calendar_max_days_off: Optional[int] = None
    calendar_created_at: Optional[datetime] = None
    calendar_updated_at: Optional[datetime] = None

    # Vacation Configuration
    vacation_config_id: Optional[str] = None
    vacation_config_name: Optional[str] = None
    vacation_config_employee_request_enabled: Optional[bool] = None
    vacation_config_needs_validation: Optional[bool] = None
    vacation_config_day_type: Optional[str] = None
    vacation_config_max_days_off: Optional[int] = None
    vacation_config_is_default: Optional[bool] = None

    # Employee (resumen)
    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[str] = None

    raw: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
