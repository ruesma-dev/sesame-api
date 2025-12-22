# sesame_connector/domain/models/tag.py
from __future__ import annotations

from typing import Optional

from pydantic import Field

from sesame_connector.domain.models.base import DomainModel


class Tag(DomainModel):
    id: str = Field(...)
    name: Optional[str] = None
