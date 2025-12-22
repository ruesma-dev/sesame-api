# sesame_connector/application/use_cases/day_off_use_cases.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.absence_day_off import AbsenceDayOff
from sesame_connector.domain.models.vacation_day_off import VacationDayOff

class DayOffUseCases:
    def __init__(self, port: SesamePort) -> None:
        self._port = port

    def list_absences(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        order_by: Optional[str] = None,
        page_size: int = 200,
        all_pages: bool = True,
    ) -> Tuple[List[AbsenceDayOff], Dict]:
        if not all_pages:
            return self._port.list_absence_day_off(
                employee_ids=employee_ids,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                page=1,
                page_size=page_size,
            )

        out: List[AbsenceDayOff] = []
        meta_last: Dict = {}
        page = 1
        while True:
            items, meta = self._port.list_absence_day_off(
                employee_ids=employee_ids,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                page=page,
                page_size=page_size,
            )
            meta_last = meta or {}
            if not items:
                break
            out.extend(items)
            current = int(meta_last.get("currentPage") or page)
            last_page = int(meta_last.get("lastPage") or current)
            if current >= last_page:
                break
            page += 1

        meta_out = dict(meta_last)
        meta_out["pages_fetched"] = page
        return out, meta_out

    def list_vacations(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        order_by: Optional[str] = None,
        page_size: int = 200,
        all_pages: bool = True,
    ) -> Tuple[List[VacationDayOff], Dict]:
        if not all_pages:
            return self._port.list_vacation_day_off(
                employee_ids=employee_ids,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                page=1,
                page_size=page_size,
            )

        out: List[VacationDayOff] = []
        meta_last: Dict = {}
        page = 1
        while True:
            items, meta = self._port.list_vacation_day_off(
                employee_ids=employee_ids,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                page=page,
                page_size=page_size,
            )
            meta_last = meta or {}
            if not items:
                break
            out.extend(items)
            current = int(meta_last.get("currentPage") or page)
            last_page = int(meta_last.get("lastPage") or current)
            if current >= last_page:
                break
            page += 1

        meta_out = dict(meta_last)
        meta_out["pages_fetched"] = page
        return out, meta_out
