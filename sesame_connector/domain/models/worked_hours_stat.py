# sesame_connector/domain/models/worked_hours_stat.py
from __future__ import annotations

from typing import Optional

from pydantic import Field

from sesame_connector.domain.models.base import DomainModel


class WorkedHoursStat(DomainModel):
    employee_id: str = Field(...)
    seconds_worked: int = 0
    seconds_to_work: Optional[int] = None
    seconds_balance: Optional[int] = None
