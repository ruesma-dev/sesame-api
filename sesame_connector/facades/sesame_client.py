# sesame_connector/facades/sesame_client.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from sesame_connector.config.settings import Settings
from sesame_connector.config.endpoints_loader import load_endpoints
from sesame_connector.infrastructure.http.http_client import HttpClient
from sesame_connector.infrastructure.repositories.sesame_repository import SesameRepositoryImpl

from sesame_connector.application.use_cases.employee_use_cases import EmployeeUseCases
from sesame_connector.application.use_cases.security_use_cases import SecurityUseCases
from sesame_connector.application.use_cases.time_analytics_use_cases import TimeAnalyticsUseCases
from sesame_connector.application.use_cases.worked_hours_use_cases import WorkedHoursUseCases
from sesame_connector.application.use_cases.day_off_use_cases import DayOffUseCases
from sesame_connector.application.use_cases.daily_attendance_use_cases import DailyAttendanceUseCases


class SesameClient:
    """
    Fachada JSON-in/JSON-out para Sesame.

    - Se construye desde .env + endpoints.yaml
    - Expone un método genérico `execute(action, payload)` pensado para ser
      llamado desde otros microservicios (o un API HTTP).
    - Internamente usa SesameRepositoryImpl + casos de uso existentes.
    """

    def __init__(
        self,
        *,
        repo: SesameRepositoryImpl,
        security_uc: SecurityUseCases,
        employee_uc: EmployeeUseCases,
        time_analytics_uc: TimeAnalyticsUseCases,
        worked_hours_uc: WorkedHoursUseCases,
        day_off_uc: DayOffUseCases,
        daily_attendance_uc: DailyAttendanceUseCases,
    ) -> None:
        self._repo = repo

        # Alias consistentes con lo que usan las acciones
        self._sec_uc = security_uc
        self._emp_uc = employee_uc
        self._ta_uc = time_analytics_uc
        self._wh_uc = worked_hours_uc
        self._dayoff_uc = day_off_uc
        self._attendance_uc = daily_attendance_uc

    # ------------------------------------------------------------------
    # Factoría: construir desde .env (para usar desde cualquier app)
    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls) -> "SesameClient":
        settings = Settings.from_env()
        http = HttpClient.from_settings(settings)

        # Usamos la ruta por defecto del loader (paquete instalado)
        endpoints = load_endpoints()

        repo = SesameRepositoryImpl(settings=settings, http=http, endpoints=endpoints)

        emp_uc = EmployeeUseCases(repo)
        sec_uc = SecurityUseCases(repo)
        wh_uc = WorkedHoursUseCases(repo)
        ta_uc = TimeAnalyticsUseCases(repo)
        day_off_uc = DayOffUseCases(repo)
        daily_attendance_uc = DailyAttendanceUseCases(repo=repo, emp_uc=emp_uc, wh_uc=wh_uc)

        return cls(
            repo=repo,
            security_uc=sec_uc,
            employee_uc=emp_uc,
            time_analytics_uc=ta_uc,
            worked_hours_uc=wh_uc,
            day_off_uc=day_off_uc,
            daily_attendance_uc=daily_attendance_uc,
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    @staticmethod
    def _dump_model(model: Any) -> Dict[str, Any]:
        """
        Convierte modelos de dominio Pydantic/dataclasses a dict JSON friendly.
        """
        if hasattr(model, "model_dump"):
            # Pydantic v2
            return model.model_dump(mode="json", exclude_none=True)  # type: ignore[no-any-return]

        if is_dataclass(model):
            return asdict(model)

        if isinstance(model, dict):
            return model

        # Fallback muy defensivo
        if hasattr(model, "dict"):
            # Pydantic v1 u otros
            return model.dict(exclude_none=True)  # type: ignore[no-any-return]

        return {"value": repr(model)}

    @classmethod
    def _dump_list(cls, models: List[Any]) -> List[Dict[str, Any]]:
        return [cls._dump_model(m) for m in models]

    @staticmethod
    def _required(payload: Dict[str, Any], key: str) -> Any:
        if key not in payload or payload[key] is None:
            raise ValueError(f"Falta campo obligatorio en payload: '{key}'")
        return payload[key]

    # ------------------------------------------------------------------
    # Punto de entrada genérico JSON-in/JSON-out
    # ------------------------------------------------------------------
    def execute(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Punto de entrada principal para otras apps/microservicios.
        """
        payload = payload or {}

        if action == "token.info":
            return self._action_token_info()

        # Employees
        if action == "employees.list":
            return self._action_employees_list(payload)

        # Work entries CRUD / clock
        if action == "work_entries.list":
            return self._action_work_entries_list(payload)
        if action == "work_entries.create":
            return self._action_work_entries_create(payload)
        if action == "work_entries.update":
            return self._action_work_entries_update(payload)
        if action == "work_entries.delete":
            return self._action_work_entries_delete(payload)
        if action == "work_entries.clock_in":
            return self._action_work_entries_clock_in(payload)
        if action == "work_entries.clock_out":
            return self._action_work_entries_clock_out(payload)

        # Time entries
        if action == "time_entries.list":
            return self._action_time_entries_list(payload)

        # Day offs (ausencias / vacaciones)
        if action == "day_off.absences.range_all_employees":
            return self._action_absences_range_all_employees(payload)
        if action == "day_off.vacations.range_all_employees":
            return self._action_vacations_range_all_employees(payload)

        # Worked hours report
        if action == "worked_hours.range_all_employees":
            return self._action_worked_hours_range_all_employees(payload)

        # Asistencia diaria (abiertos/cerrados, horas trabajadas vs teóricas)
        if action == "work_entries.status_today_all_employees":
            return self._action_work_entries_status_today_all_employees(payload)

        raise ValueError(f"Acción no soportada: {action!r}")

    # ------------------------------------------------------------------
    # Acciones concretas
    # ------------------------------------------------------------------
    # 1) Seguridad / compañía
    def _action_token_info(self) -> Dict[str, Any]:
        """
        Devuelve info del token + compañía.
        """
        return self._sec_uc.show_token_info()

    # 2) Employees
    def _action_employees_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entrada JSON:
          {
            "only_active": true/false/null,   # opcional
            "page_size": 200                  # opcional
          }
        """
        only_active = payload.get("only_active", None)
        page_size = int(payload.get("page_size", 100))

        employees = self._emp_uc.list_employees(
            only_active=only_active,
            page_size=page_size,
        )

        data = self._dump_list(employees)
        return {
            "data": data,
            "meta": {
                "count": len(data),
                "only_active": only_active,
            },
        }

    # 3) Work entries: LIST
    def _action_work_entries_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = self._required(payload, "employee_id")
        date_from = self._required(payload, "date_from")
        date_to = self._required(payload, "date_to")

        page_size = int(payload.get("page_size", 100))
        all_pages = bool(payload.get("all_pages", True))
        order_by = payload.get("order_by")
        page = int(payload.get("page", 1))

        if not all_pages:
            entries = self._repo.list_work_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=page_size,
                order_by=order_by,
            )
            data = self._dump_list(entries)
            return {
                "data": data,
                "meta": {
                    "employee_id": employee_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "page": page,
                    "page_size": page_size,
                    "all_pages": False,
                    "count": len(data),
                },
            }

        # Modo "traer todo"
        out: List[Any] = []
        current_page = 1
        while True:
            chunk = self._repo.list_work_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                page=current_page,
                page_size=page_size,
                order_by=order_by,
            )
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            current_page += 1

        data = self._dump_list(out)
        return {
            "data": data,
            "meta": {
                "employee_id": employee_id,
                "date_from": date_from,
                "date_to": date_to,
                "page_size": page_size,
                "all_pages": True,
                "pages_fetched": current_page,
                "count": len(data),
            },
        }

    # 4) Work entries: CREATE
    def _action_work_entries_create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = self._required(payload, "employee_id")
        work_entry_type = payload.get("work_entry_type")
        work_check_type_id = payload.get("work_check_type_id")
        work_break_id = payload.get("work_break_id")

        pin = payload.get("in") or {}
        pout = payload.get("out") or {}

        entry = self._repo.create_work_entry(
            employee_id=employee_id,
            work_entry_type=work_entry_type,
            work_check_type_id=work_check_type_id,
            work_break_id=work_break_id,
            in_at=pin.get("at"),
            in_latitude=pin.get("latitude"),
            in_longitude=pin.get("longitude"),
            in_office_id=pin.get("office_id"),
            out_at=pout.get("at"),
            out_latitude=pout.get("latitude"),
            out_longitude=pout.get("longitude"),
            out_office_id=pout.get("office_id"),
        )

        return {"data": self._dump_model(entry)}

    # 5) Work entries: UPDATE
    def _action_work_entries_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        work_entry_id = self._required(payload, "work_entry_id")
        work_entry_type = payload.get("work_entry_type")

        pin = payload.get("in") or {}
        pout = payload.get("out") or {}

        entry = self._repo.update_work_entry(
            work_entry_id=work_entry_id,
            work_entry_type=work_entry_type,
            in_at=pin.get("at"),
            in_latitude=pin.get("latitude"),
            in_longitude=pin.get("longitude"),
            in_office_id=pin.get("office_id"),
            out_at=pout.get("at"),
            out_latitude=pout.get("latitude"),
            out_longitude=pout.get("longitude"),
            out_office_id=pout.get("office_id"),
        )
        return {"data": self._dump_model(entry)}

    # 6) Work entries: DELETE
    def _action_work_entries_delete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        work_entry_id = self._required(payload, "work_entry_id")
        self._repo.delete_work_entry(work_entry_id=work_entry_id)
        return {"ok": True, "work_entry_id": work_entry_id}

    # 7) Work entries: CLOCK-IN
    def _action_work_entries_clock_in(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = self._required(payload, "employee_id")
        coords = payload.get("coordinates") or {}
        work_check_type_id = payload.get("work_check_type_id")
        work_break_id = payload.get("work_break_id")

        entry = self._repo.clock_in(
            employee_id=employee_id,
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
            work_check_type_id=work_check_type_id,
            work_break_id=work_break_id,
        )
        return {"data": self._dump_model(entry)}

    # 8) Work entries: CLOCK-OUT
    def _action_work_entries_clock_out(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = self._required(payload, "employee_id")
        coords = payload.get("coordinates") or {}

        entry = self._repo.clock_out(
            employee_id=employee_id,
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
        )
        return {"data": self._dump_model(entry)}

    # 9) Time entries: LIST
    def _action_time_entries_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = payload.get("employee_id")
        date_from = payload.get("date_from")
        date_to = payload.get("date_to")
        employee_status = payload.get("employee_status", "active")
        page_size = int(payload.get("page_size", 100))
        all_pages = bool(payload.get("all_pages", True))
        page = int(payload.get("page", 1))

        if not all_pages:
            items = self._repo.list_time_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                employee_status=employee_status,
                page=page,
                page_size=page_size,
            )
            data = self._dump_list(items)
            return {
                "data": data,
                "meta": {
                    "page": page,
                    "page_size": page_size,
                    "all_pages": False,
                    "count": len(data),
                },
            }

        out: List[Any] = []
        current_page = 1
        while True:
            chunk = self._repo.list_time_entries(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to,
                employee_status=employee_status,
                page=current_page,
                page_size=page_size,
            )
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            current_page += 1

        data = self._dump_list(out)
        return {
            "data": data,
            "meta": {
                "page_size": page_size,
                "pages_fetched": current_page,
                "all_pages": True,
                "count": len(data),
            },
        }

    # 10) Day Offs: AUSENCIAS
    def _action_absences_range_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        date_from = self._required(payload, "date_from")
        date_to = self._required(payload, "date_to")

        absences = self._dayoff_uc.list_absences_all_employees_range(
            date_from=date_from,
            date_to=date_to,
        )
        data = self._dump_list(absences)
        return {
            "data": data,
            "meta": {
                "date_from": date_from,
                "date_to": date_to,
                "count": len(data),
                "scope": "all_active_employees",
                "type": "absence",
            },
        }

    # 11) Day Offs: VACACIONES
    def _action_vacations_range_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        date_from = self._required(payload, "date_from")
        date_to = self._required(payload, "date_to")

        vacations = self._dayoff_uc.list_vacations_all_employees_range(
            date_from=date_from,
            date_to=date_to,
        )
        data = self._dump_list(vacations)
        return {
            "data": data,
            "meta": {
                "date_from": date_from,
                "date_to": date_to,
                "count": len(data),
                "scope": "all_active_employees",
                "type": "vacation",
            },
        }

    # 12) Worked Hours Report: rango, todos los empleados
    def _action_worked_hours_range_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        date_from = self._required(payload, "date_from")
        date_to = self._required(payload, "date_to")
        with_checks = bool(payload.get("with_checks", False))

        stats = self._wh_uc.list_worked_hours_all_employees_range(
            date_from=date_from,
            date_to=date_to,
            with_checks=with_checks,
        )
        data = self._dump_list(stats)
        return {
            "data": data,
            "meta": {
                "date_from": date_from,
                "date_to": date_to,
                "count": len(data),
                "with_checks": with_checks,
            },
        }

    # 13) Asistencia diaria: abiertos / cerrados / sin fichajes
    def _action_work_entries_status_today_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve JSON con:
          - open: fichajes abiertos hoy
          - closed: fichajes cerrados hoy + info de horas trabajadas/teóricas
          - no_entries: empleados activos sin fichajes hoy
        """
        date_str: Optional[str] = payload.get("date")
        if not date_str:
            date_str = date.today().isoformat()

        summary = self._attendance_uc.build_status_for_date(date_str=date_str)

        open_rows = [self._dump_model(r) for r in summary.open_entries]
        closed_rows = [self._dump_model(r) for r in summary.closed_entries]
        no_entries_rows = [self._dump_model(r) for r in summary.no_entries]

        return {
            "data": {
                "open": open_rows,
                "closed": closed_rows,
                "no_entries": no_entries_rows,
            },
            "meta": {
                "date": summary.date,
                "active_employees": summary.active_employees,
                "open_count": len(open_rows),
                "closed_count": len(closed_rows),
                "no_entries_count": len(no_entries_rows),
                "closed_met_schedule_count": summary.closed_met_schedule_count,
                "closed_not_met_schedule_count": summary.closed_not_met_schedule_count,
            },
        }
