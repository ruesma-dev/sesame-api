# domain/models/work_entry.py
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class WorkEntry(BaseModel):
    """Modelo aplanado y tolerante para /schedule/v1/work-entries."""
    id: Optional[str] = Field(default=None)
    work_check_type_id: Optional[str] = None
    work_entry_type: Optional[str] = None

    # Employee (resumen)
    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[EmailStr] = None

    # IN
    in_origin: Optional[str] = None
    in_at: Optional[datetime] = None
    in_latitude: Optional[float] = None
    in_longitude: Optional[float] = None
    in_office_id: Optional[str] = None

    # OUT
    out_origin: Optional[str] = None
    out_at: Optional[datetime] = None
    out_latitude: Optional[float] = None
    out_longitude: Optional[float] = None
    out_office_id: Optional[str] = None

    worked_seconds: Optional[int] = None

    # Trazas
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    raw: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
