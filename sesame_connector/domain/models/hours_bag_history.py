# sesame_connector/domain/models/hours_bag_history.py
from __future__ import annotations

import datetime as dt
from typing import Optional

from sesame_connector.domain.models.base import DomainModel


class HoursBagHistory(DomainModel):
    id: str

    # Ojo: mismo patrón (campo "date" con tipo date)
    date: Optional[dt.date] = None

    seconds: Optional[int] = None
    check_seconds: Optional[int] = None
    check_seconds_with_variation: Optional[int] = None

    hours_bag_rule_id: Optional[str] = None
    hours_bag_rule_name: Optional[str] = None
    hours_bag_rule_variation: Optional[float] = None

    employee_id: Optional[str] = None
    employee_name: Optional[str] = None

    raw: Optional[dict] = None

    model_config = {"extra": "allow"}
