# sesame_connector/domain/models/time_entry.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from sesame_connector.domain.models.base import DomainModel
from sesame_connector.domain.models.project import Project
from sesame_connector.domain.models.tag import Tag


class TimeEntry(DomainModel):
    id: str = Field(...)

    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[str] = None

    project: Optional[Project] = None

    tags: List[Tag] = Field(default_factory=list)

    time_entry_in_at: Optional[datetime] = None
    time_entry_out_at: Optional[datetime] = None

    in_latitude: Optional[float] = None
    in_longitude: Optional[float] = None
    out_latitude: Optional[float] = None
    out_longitude: Optional[float] = None

    comment: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    raw: Optional[Dict[str, Any]] = None

    @property
    def is_open(self) -> bool:
        return self.time_entry_in_at is not None and self.time_entry_out_at is None

    @property
    def employee_display_name(self) -> str:
        return " ".join([x for x in [self.employee_first_name, self.employee_last_name] if x]).strip()
