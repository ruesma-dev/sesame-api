# sesame_connector/domain/models/base.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
