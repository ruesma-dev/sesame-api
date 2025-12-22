# sesame_connector/application/use_cases/worked_hours_use_cases.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.worked_hours_stat import WorkedHoursStat


class WorkedHoursUseCases:
    def __init__(self, port: SesamePort) -> None:
        self._port = port

    def list_worked_hours(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        with_checks: bool = False,
        page_size: int = 200,
        all_pages: bool = True,
    ) -> Tuple[List[WorkedHoursStat], Dict]:
        if not all_pages:
            return self._port.list_worked_hours_report(
                employee_ids=employee_ids,
                date_from=date_from,
                date_to=date_to,
                with_checks=with_checks,
                page=1,
                page_size=page_size,
            )

        out: List[WorkedHoursStat] = []
        meta_last: Dict = {}
        page = 1
        while True:
            items, meta = self._port.list_worked_hours_report(
                employee_ids=employee_ids,
                date_from=date_from,
                date_to=date_to,
                with_checks=with_checks,
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
