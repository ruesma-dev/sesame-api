# sesame_connector/facades/sesame_client.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

# Nota:
# - Si bootstrap.py está en la raíz del repo, esto funciona: from bootstrap import build_container
# - Si en el futuro lo mueves a sesame_connector/bootstrap.py, funcionará el fallback.
try:
    from bootstrap import build_container  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from sesame_connector.bootstrap import build_container  # type: ignore

from sesame_connector.domain.models.base import DomainModel


class SesameClient:
    """
    Fachada JSON-in/JSON-out:
      - pensada para ser invocada por otros servicios o por CLI
      - evita acoplar el resto de capas a requests/pydantic.
    """

    def __init__(self) -> None:
        self._c = build_container()

    @classmethod
    def from_env(cls) -> "SesameClient":
        """
        Constructor estándar.

        En este proyecto, la configuración (.env / Settings) se resuelve dentro de build_container(),
        así que aquí simplemente devolvemos una instancia ya cableada.
        """
        return cls()

    @staticmethod
    def _dump(obj: Any) -> Any:
        if isinstance(obj, DomainModel):
            return obj.model_dump(mode="json", exclude_none=True)
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, list):
            return [SesameClient._dump(x) for x in obj]
        if isinstance(obj, dict):
            return {k: SesameClient._dump(v) for k, v in obj.items()}
        return obj

    def execute(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}

        # -------- Employees --------
        if action == "employees.list":
            only_active = payload.get("only_active", True)
            employees = self._c.employees_uc.list_employees(only_active=only_active, page_size=200)
            return {"data": self._dump(employees), "meta": {"count": len(employees)}}

        # -------- Projects --------
        if action == "projects.list":
            projects = self._c.projects_uc.list_projects(page_size=100)
            return {"data": self._dump(projects), "meta": {"count": len(projects)}}

        # -------- Time entries (tareas) --------
        if action == "time_entries.list":
            items, meta = self._c.time_entries_uc.list_time_entries(
                employee_id=payload.get("employee_id"),
                date_from=payload.get("date_from"),
                date_to=payload.get("date_to"),
                employee_status=payload.get("employee_status", "active"),
                all_pages=bool(payload.get("all_pages", True)),
                page_size=int(payload.get("page_size", 200)),
            )
            rows = self._c.time_entries_uc.to_rows(items)
            return {"data": self._dump(rows), "meta": self._dump(meta)}

        if action == "time_entries.start":
            emp_id = payload["employee_id"]
            project_id = payload["project_id"]
            tag_ids = payload["tag_ids"]
            comment = payload.get("comment")
            coords = payload.get("coordinates")
            res = self._c.time_entries_uc.start(
                employee_id=emp_id,
                project_id=project_id,
                tag_ids=tag_ids,
                comment=comment,
                coordinates=coords,
            )
            return {"data": self._dump(res)}

        if action == "time_entries.stop":
            emp_id = payload["employee_id"]
            comment = payload.get("comment")
            coords = payload.get("coordinates")
            res = self._c.time_entries_uc.stop(employee_id=emp_id, comment=comment, coordinates=coords)
            return {"data": self._dump(res)}

        if action == "time_entries.update":
            time_entry_id = payload["time_entry_id"]
            res = self._c.time_entries_uc.update(time_entry_id=time_entry_id, payload=payload["payload"])
            return {"data": self._dump(res)}

        if action == "time_entries.delete":
            time_entry_id = payload["time_entry_id"]
            ok = self._c.time_entries_uc.delete(time_entry_id=time_entry_id)
            return {"ok": ok, "time_entry_id": time_entry_id}

        # -------- Work entries (fichajes) --------
        if action == "work_entries.list":
            items = self._c.work_entries_uc.list_work_entries(
                employee_id=payload["employee_id"],
                date_from=payload["date_from"],
                date_to=payload["date_to"],
                all_pages=bool(payload.get("all_pages", True)),
                page_size=int(payload.get("page_size", 200)),
                order_by=payload.get("order_by", "workEntryIn.date asc"),
            )
            return {"data": self._dump(items), "meta": {"count": len(items)}}

        if action == "work_entries.create":
            entry = self._c.work_entries_uc.create(payload=payload["payload"])
            return {"data": self._dump(entry)}

        if action == "work_entries.update":
            entry = self._c.work_entries_uc.update(work_entry_id=payload["work_entry_id"], payload=payload["payload"])
            return {"data": self._dump(entry)}

        if action == "work_entries.delete":
            ok = self._c.work_entries_uc.delete(work_entry_id=payload["work_entry_id"])
            return {"ok": ok, "work_entry_id": payload["work_entry_id"]}

        if action == "work_entries.clock_in":
            entry = self._c.work_entries_uc.clock_in(payload=payload["payload"])
            return {"data": self._dump(entry)}

        if action == "work_entries.clock_out":
            entry = self._c.work_entries_uc.clock_out(payload=payload["payload"])
            return {"data": self._dump(entry)}

        # -------- Worked hours --------
        if action == "worked_hours.list":
            employee_ids = payload.get("employee_ids")
            items, meta = self._c.worked_hours_uc.list_worked_hours(
                employee_ids=employee_ids,
                date_from=payload["date_from"],
                date_to=payload["date_to"],
                with_checks=bool(payload.get("with_checks", False)),
                all_pages=bool(payload.get("all_pages", True)),
            )
            return {"data": self._dump(items), "meta": self._dump(meta)}

        # -------- Day offs --------
        if action == "day_off.absences":
            items, meta = self._c.day_off_uc.list_absences(
                employee_ids=payload.get("employee_ids"),
                date_from=payload["date_from"],
                date_to=payload["date_to"],
                all_pages=bool(payload.get("all_pages", True)),
            )
            return {"data": self._dump(items), "meta": self._dump(meta)}

        if action == "day_off.vacations":
            items, meta = self._c.day_off_uc.list_vacations(
                employee_ids=payload.get("employee_ids"),
                date_from=payload["date_from"],
                date_to=payload["date_to"],
                all_pages=bool(payload.get("all_pages", True)),
            )
            return {"data": self._dump(items), "meta": self._dump(meta)}

        # -------- Metrics (bloque) --------
        if action == "metrics.extract":
            res = self._c.employee_metrics_uc.extract(
                date_from=payload["date_from"],
                date_to=payload["date_to"],
                employee_ids=payload.get("employee_ids"),
                only_active=bool(payload.get("only_active", True)),
            )
            return {"data": self._dump(res)}

        raise ValueError(f"Acción no soportada: {action!r}")
