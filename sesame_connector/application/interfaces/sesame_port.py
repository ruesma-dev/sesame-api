# sesame_connector/application/ports/sesame_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from sesame_connector.domain.models.absence_day_off import AbsenceDayOff
from sesame_connector.domain.models.employee import Employee
from sesame_connector.domain.models.project import Project
from sesame_connector.domain.models.time_entry import TimeEntry
from sesame_connector.domain.models.vacation_day_off import VacationDayOff
from sesame_connector.domain.models.work_entry import WorkEntry
from sesame_connector.domain.models.worked_hours_stat import WorkedHoursStat


class SesamePort(ABC):
    # Security / company
    @abstractmethod
    def get_token_info_raw(self) -> Dict:
        raise NotImplementedError

    # Employees
    @abstractmethod
    def list_employees(
        self,
        *,
        only_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[Employee]:
        raise NotImplementedError

    # Projects
    @abstractmethod
    def list_projects(self, *, page: int = 1, page_size: int = 100) -> List[Project]:
        raise NotImplementedError

    # Time entries
    @abstractmethod
    def list_time_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        employee_status: str = "active",
        page: int = 1,
        page_size: int = 200,
    ) -> List[TimeEntry]:
        raise NotImplementedError

    # Work entries
    @abstractmethod
    def list_work_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        order_by: Optional[str] = None,
    ) -> List[WorkEntry]:
        raise NotImplementedError

    # Worked hours report
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
    ) -> Tuple[List[WorkedHoursStat], Dict]:
        raise NotImplementedError

    # Day offs
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
    ) -> Tuple[List[AbsenceDayOff], Dict]:
        raise NotImplementedError

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
    ) -> Tuple[List[VacationDayOff], Dict]:
        raise NotImplementedError
