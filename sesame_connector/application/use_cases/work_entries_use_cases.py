# sesame_connector/application/use_cases/work_entries_use_cases.py
from __future__ import annotations

from typing import Dict, List, Optional

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.work_entry import WorkEntry


class WorkEntriesUseCases:
    def __init__(self, port: SesamePort) -> None:
        self._port = port

    def list_work_entries(
        self,
        *,
        employee_id: str,
        date_from: str,
        date_to: str,
        page_size: int = 200,
        all_pages: bool = True,
        order_by: Optional[str] = "workEntryIn.date asc",
    ) -> List[WorkEntry]:
        if not all_pages:
            return self._port.list_work_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                page=1,
                page_size=page_size,
                order_by=order_by,
            )

        out: List[WorkEntry] = []
        page = 1
        while True:
            chunk = self._port.list_work_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
                order_by=order_by,
            )
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
        return out

    def create(self, *, payload: Dict) -> WorkEntry:
        return self._port.create_work_entry(payload=payload)

    def update(self, *, work_entry_id: str, payload: Dict) -> WorkEntry:
        return self._port.update_work_entry(work_entry_id=work_entry_id, payload=payload)

    def delete(self, *, work_entry_id: str) -> bool:
        return self._port.delete_work_entry(work_entry_id=work_entry_id)

    def clock_in(self, *, payload: Dict) -> WorkEntry:
        return self._port.clock_in(payload=payload)

    def clock_out(self, *, payload: Dict) -> WorkEntry:
        return self._port.clock_out(payload=payload)
