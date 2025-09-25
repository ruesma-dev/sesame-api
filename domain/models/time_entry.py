# domain/models/time_entry.py
from __future__ import annotations
# domain/models/time_entry.py

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class TimeEntry(BaseModel):
    """Modelo aplanado y tolerante para /project/v1/time-entries."""
    id: Optional[str] = Field(default=None)

    # Employee (resumen)
    employee_id: Optional[str] = None
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_email: Optional[EmailStr] = None

    # Campos propios de time entry
    project_id: Optional[str] = None
    tag_ids: Optional[List[str]] = None

    # IN / OUT con coordenadas
    in_at: Optional[datetime] = None
    in_latitude: Optional[float] = None
    in_longitude: Optional[float] = None

    out_at: Optional[datetime] = None
    out_latitude: Optional[float] = None
    out_longitude: Optional[float] = None

    comment: Optional[str] = None

    # Trazas
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    # Contenedor para conservar payloads no mapeados
    raw: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
