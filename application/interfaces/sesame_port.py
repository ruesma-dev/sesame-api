# application/interfaces/sesame_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Dict, Any

from domain.models.employee import Employee
from domain.models.token_info import TokenInfo
from domain.models.time_entry import TimeEntry
from domain.models.work_entry import WorkEntry
from domain.models.hours_bag_history import HoursBagHistory


class SesamePort(ABC):
    """Puerto (interface) para la API de Sesame."""

    # --- Seguridad / compañía ---
    @abstractmethod
    def get_token_info(self) -> TokenInfo:
        ...
    @abstractmethod
    def get_token_info_raw(self) -> Dict[str, Any]:
        ...

    # --- Empleados ---
    @abstractmethod
    def list_employees(
        self, *, only_active: Optional[bool] = None, page: int = 1, page_size: int = 100
    ) -> List[Employee]:
        ...

    @abstractmethod
    def create_employee(self, employee: Employee) -> Employee:
        ...

    @abstractmethod
    def bulk_create_employees(self, employees: Iterable[Employee]) -> List[Employee]:
        ...

    # --- Time entries (GET) ---
    @abstractmethod
    def list_time_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[TimeEntry]:
        ...

    # --- Work entries (GET/POST/PUT/DELETE + clock-in/out) ---
    @abstractmethod
    def list_work_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[WorkEntry]:
        ...

    @abstractmethod
    def create_work_entry(self, payload: Dict[str, Any]) -> WorkEntry:
        ...

    @abstractmethod
    def update_work_entry(self, work_entry_id: str, payload: Dict[str, Any]) -> WorkEntry:
        ...

    @abstractmethod
    def delete_work_entry(self, work_entry_id: str) -> bool:
        ...

    @abstractmethod
    def clock_in(
        self,
        *,
        employee_id: str,
        coordinates: Optional[Dict[str, float]] = None,
        work_check_type_id: Optional[str] = None,
        work_break_id: Optional[str] = None,
    ) -> WorkEntry:
        ...

    @abstractmethod
    def clock_out(
        self,
        *,
        employee_id: str,
        coordinates: Optional[Dict[str, float]] = None,
    ) -> WorkEntry:
        ...

    # --- Hours bag (bolsa de horas) ---
    @abstractmethod
    def list_hours_bag_rule_history(
        self,
        *,
        date_from: Optional[str],
        date_to: Optional[str],
        employee_ids: Optional[List[str]] = None,
        hours_bag_rule_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[HoursBagHistory]:
        ...
