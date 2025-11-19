# domain/models/task.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Task(BaseModel):
    """
    Tarea genérica que se abre cuando alguien ha cumplido su horario.

    Esto NO sabe nada de Business Central. Es un modelo neutro
    que luego un adaptador puede transformar al formato que
    necesite BC o tu BBDD central.
    """
    id: Optional[str] = None

    employee_id: str
    start_at: datetime
    description: str

    # Metadatos útiles para otros sistemas
    source: str = "sesame_daily_attendance"
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
