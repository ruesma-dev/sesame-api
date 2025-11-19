# application/interfaces/sesame_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional, Tuple

from sesame_connector.domain.models.employee import Employee
from sesame_connector.domain.models.token_info import TokenInfo
from sesame_connector.domain.models.time_entry import TimeEntry
from sesame_connector.domain.models.work_entry import WorkEntry
from sesame_connector.domain.models.hours_bag_history import HoursBagHistory
from sesame_connector.domain.models.employee_office_assignation import EmployeeOfficeAssignation
from sesame_connector.domain.models.worked_hours_stat import WorkedHoursStat
from sesame_connector.domain.models.absence_day_off import AbsenceDayOff
from sesame_connector.domain.models.vacation_day_off import VacationDayOff


class SesamePort(ABC):
    # ─────────── Security / Company ───────────
    @abstractmethod
    def get_token_info(self) -> TokenInfo: ...

    @abstractmethod
    def get_token_info_raw(self) -> Dict: ...

    # ─────────── Employees ───────────
    @abstractmethod
    def list_employees(
        self,
        *,
        only_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[Employee]: ...

    @abstractmethod
    def create_employee(self, employee: Employee) -> Employee: ...

    @abstractmethod
    def bulk_create_employees(self, employees: Iterable[Employee]) -> List[Employee]: ...

    # ─────────── Project: time entries ───────────
    @abstractmethod
    def list_time_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        extra_params: Optional[Dict] = None,
    ) -> List[TimeEntry]: ...

    # ─────────── Schedule: work entries ───────────
    @abstractmethod
    def list_work_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        extra_params: Optional[Dict] = None,
    ) -> List[WorkEntry]: ...

    @abstractmethod
    def create_work_entry(self, payload: Dict) -> WorkEntry: ...

    @abstractmethod
    def update_work_entry(self, work_entry_id: str, payload: Dict) -> WorkEntry: ...

    @abstractmethod
    def delete_work_entry(self, work_entry_id: str) -> bool: ...

    @abstractmethod
    def clock_in(
        self,
        *,
        employee_id: str,
        coordinates: Optional[Dict] = None,
        work_check_type_id: Optional[str] = None,
        work_break_id: Optional[str] = None,
    ) -> WorkEntry: ...

    @abstractmethod
    def clock_out(
        self,
        *,
        employee_id: str,
        coordinates: Optional[Dict] = None,
    ) -> WorkEntry: ...

    # ─────────── Hours Bag ───────────
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
    ) -> List[HoursBagHistory]: ...

    # ─────────── Employee Office Assignations ───────────
    @abstractmethod
    def list_employee_office_assignations(
        self,
        *,
        employee_id: Optional[str] = None,
        office_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[EmployeeOfficeAssignation]: ...

    # ─────────── Worked Hours Report ───────────
    @abstractmethod
    def list_worked_hours_report(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        with_checks: Optional[bool] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[WorkedHoursStat], Dict]: ...

    # ─────────── NEW: Day Offs ───────────
    @abstractmethod
    def list_absence_day_off(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[AbsenceDayOff], Dict]: ...

    @abstractmethod
    def list_vacation_day_off(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[VacationDayOff], Dict]: ...
