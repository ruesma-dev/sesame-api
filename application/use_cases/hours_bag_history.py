# domain/models/hours_bag_history.py
from __future__ import annotations

from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel


class HoursBagHistory(BaseModel):
    id: str
    date: date

    # segundos base del movimiento
    seconds: Optional[int] = None

    # chequeos que aporta la API
    check_seconds: Optional[int] = None
    check_seconds_with_variation: Optional[int] = None

    # regla aplicada
    hours_bag_rule_id: Optional[str] = None
    hours_bag_rule_name: Optional[str] = None
    hours_bag_rule_variation: Optional[float] = None

    # empleado
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None

    # crudos / trazas por si hace falta debug
    raw: Optional[dict] = None
