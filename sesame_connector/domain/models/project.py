# sesame_connector/domain/models/project.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from sesame_connector.domain.models.base import DomainModel


class Project(DomainModel):
    id: str = Field(...)
    name: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None
