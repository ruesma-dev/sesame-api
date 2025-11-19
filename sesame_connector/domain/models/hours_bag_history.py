# domain/models/hours_bag_history.py
from __future__ import annotations

from typing import Optional
from datetime import date
from pydantic import BaseModel


class HoursBagHistory(BaseModel):
    id: str
    # Puede venir ausente o null en algunos movimientos → hacerlo opcional
    date: Optional[date] = None

    # segundos base del movimiento
    seconds: Optional[int] = None

    # métricas adicionales de la API
    check_seconds: Optional[int] = None
    check_seconds_with_variation: Optional[int] = None

    # regla de bolsa
    hours_bag_rule_id: Optional[str] = None
    hours_bag_rule_name: Optional[str] = None
    hours_bag_rule_variation: Optional[float] = None

    # empleado
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None

    # crudo
    raw: Optional[dict] = None
