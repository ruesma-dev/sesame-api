# domain/models/token_info.py
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel

class CompanyInfo(BaseModel):
    id: str
    name: str | None = None
    notification_email: str | None = None
    language: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class TokenInfo(BaseModel):
    company: CompanyInfo
