# domain/models/employee_office_assignation.py
from __future__ import annotations

from typing import Optional, Dict, Any

from pydantic import BaseModel


class EmployeeOfficeAssignation(BaseModel):
    id: str
    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[str] = None

    office_id: Optional[str] = None
    office_name: Optional[str] = None
    office_address: Optional[str] = None
    office_latitude: Optional[float] = None
    office_longitude: Optional[float] = None
    office_description: Optional[str] = None
    office_radius: Optional[float] = None
    office_default_timezone: Optional[str] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    raw: Optional[Dict[str, Any]] = None
