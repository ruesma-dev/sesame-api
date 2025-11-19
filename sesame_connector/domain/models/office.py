# domain/models/office.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Office(BaseModel):
    id: str
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    radius: Optional[float] = None
    default_timezone: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
