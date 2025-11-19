# application/interfaces/task_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from sesame_connector.domain.models.task import Task


class TaskPort(ABC):
    """
    Puerto de aplicación para trabajar con tareas.

    La implementación concreta (infraestructura) podrá:
      - llamar a Business Central,
      - guardar en PostgreSQL,
      - publicar en una cola, etc.
    """

    @abstractmethod
    def create_task(self, task: Task) -> Task:
        """Crea una única tarea y devuelve la tarea creada (con id si aplica)."""
        raise NotImplementedError

    @abstractmethod
    def bulk_create_tasks(self, tasks: Iterable[Task]) -> List[Task]:
        """Crea varias tareas de golpe (opcionalmente optimizado)."""
        raise NotImplementedError
