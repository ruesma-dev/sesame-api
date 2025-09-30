# domain/models/worked_hours_stat.py
from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel


class WorkedHoursStat(BaseModel):
    employee_id: str
    seconds_worked: int
    seconds_to_work: Optional[int] = None
    seconds_balance: Optional[int] = None
    checks: Optional[List[Any]] = None  # solo si withChecks=true

    model_config = {"extra": "allow"}
