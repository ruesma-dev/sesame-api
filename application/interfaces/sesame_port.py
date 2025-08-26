# application/interfaces/sesame_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from domain.models.employee import Employee
from domain.models.token_info import TokenInfo


class SesamePort(ABC):
    """Puerto (interface hexagonal) para operar con la API de Sesame."""

    @abstractmethod
    def get_token_info(self) -> TokenInfo:
        """Devuelve información asociada al token (compañía, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def list_employees(
        self,
        *,
        only_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> List[Employee]:
        """Devuelve empleados con paginación simple."""
        raise NotImplementedError

    @abstractmethod
    def create_employee(self, employee: Employee) -> Employee:
        """Crea un empleado en Sesame y devuelve el empleado con id asignado."""
        raise NotImplementedError

    @abstractmethod
    def bulk_create_employees(self, employees: Iterable[Employee]) -> List[Employee]:
        """Crea empleados en lote (si la API lo soporta); fallback a bucle."""
        raise NotImplementedError
