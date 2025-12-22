# sesame_connector/application/use_cases/time_entries_use_cases.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.time_entry import TimeEntry


class TimeEntriesUseCases:
    def __init__(self, port: SesamePort) -> None:
        self._port = port

    def list_time_entries(
        self,
        *,
        employee_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        employee_status: str = "active",
        page_size: int = 200,
        all_pages: bool = True,
    ) -> Tuple[List[TimeEntry], Dict]:
        if not all_pages:
            return self._port.list_time_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                employee_status=employee_status,
                page=1,
                page_size=page_size,
            )

        out: List[TimeEntry] = []
        meta_last: Dict = {}
        page = 1
        while True:
            items, meta = self._port.list_time_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                employee_status=employee_status,
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

    def start(
        self,
        *,
        employee_id: str,
        project_id: str,
        tag_ids: List[str],
        comment: Optional[str] = None,
        coordinates: Optional[Dict] = None,
    ) -> Dict:
        return self._port.start_time_entry(
            employee_id=employee_id,
            project_id=project_id,
            tag_ids=tag_ids,
            comment=comment,
            coordinates=coordinates,
        )

    def stop(
        self,
        *,
        employee_id: str,
        comment: Optional[str] = None,
        coordinates: Optional[Dict] = None,
    ) -> Dict:
        return self._port.stop_time_entry(
            employee_id=employee_id,
            comment=comment,
            coordinates=coordinates,
        )

    def update(self, *, time_entry_id: str, payload: Dict) -> Dict:
        return self._port.update_time_entry(time_entry_id=time_entry_id, payload=payload)

    def delete(self, *, time_entry_id: str) -> bool:
        return self._port.delete_time_entry(time_entry_id=time_entry_id)

    @staticmethod
    def to_rows(entries: List[TimeEntry]) -> List[Dict[str, object]]:
        """
        Filas “human friendly”:
          - proyecto + tareas (tags)
          - abierta/cerrada
          - createdAt e imputación (in/out)
        """
        rows: List[Dict[str, object]] = []
        for e in entries:
            prj = e.project
            rows.append(
                {
                    "time_entry_id": e.id,
                    "employee_id": e.employee_id,
                    "employee_name": e.employee_display_name or None,
                    "project_id": prj.id if prj else None,
                    "project_name": prj.name if prj else None,
                    "is_open": e.is_open,
                    "created_at": e.created_at,
                    "in_at": e.time_entry_in_at,
                    "out_at": e.time_entry_out_at,
                    "comment": e.comment,
                    "tags": [{"id": t.id, "name": t.name} for t in (e.tags or [])],
                }
            )
        return rows
