# sesame_connector/domain/models/employee.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import EmailStr, Field

from sesame_connector.domain.models.base import DomainModel


class Employee(DomainModel):
    id: str = Field(...)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    work_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def display_name(self) -> str:
        return " ".join([x for x in [self.first_name, self.last_name] if x]).strip()
