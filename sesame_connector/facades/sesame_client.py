# interface_adapters/facades/sesame_client.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import date, datetime


from application.interfaces.sesame_port import SesamePort
from application.use_cases.employee_use_cases import EmployeeUseCases
from application.use_cases.day_off_use_cases import DayOffUseCases
from application.use_cases.security_use_cases import SecurityUseCases
from application.use_cases.worked_hours_use_cases import WorkedHoursUseCases
from config.endpoints_loader import load_endpoints
from config.settings import Settings
from infrastructure.http.http_client import HttpClient
from infrastructure.repositories.sesame_repository import SesameRepositoryImpl


class SesameClient:
    """
    Fachada JSON-in/JSON-out para Sesame.

    - Se construye desde .env + endpoints.yaml
    - Expone un método genérico `execute(action, payload)` pensado para ser
      llamado desde otros microservicios (o un API HTTP).
    - Internamente usa SesameRepositoryImpl + casos de uso existentes.
    """

    def __init__(self, repo: SesamePort) -> None:
        self._repo = repo
        self._sec_uc = SecurityUseCases(repo)
        self._emp_uc = EmployeeUseCases(repo)
        self._wh_uc = WorkedHoursUseCases(repo)
        self._dayoff_uc = DayOffUseCases(repo)

    # ------------------------------------------------------------------
    # Factoría: construir desde .env (para usar desde cualquier app)
    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls, endpoints_path: str | None = None) -> "SesameClient":
        """
        Crea una instancia lista para usar leyendo credenciales del entorno
        y endpoints del YAML.

        Si endpoints_path es None, usa el endpoints.yaml que viene dentro del
        propio proyecto/librería (carpeta config en la raíz del repo/paquete).
        """
        settings = Settings.from_env()

        if endpoints_path is None:
            # Ruta al archivo actual: .../sesame_connector/facades/sesame_client.py
            here = Path(__file__).resolve()
            # Raíz del proyecto/librería: subimos dos niveles
            project_root = here.parents[2]
            ep_path = project_root / "config" / "endpoints.yaml"
        else:
            ep_path = Path(endpoints_path)

        endpoints = load_endpoints(str(ep_path))
        http = HttpClient.from_settings(settings)
        repo = SesameRepositoryImpl(settings, http, endpoints=endpoints)
        return cls(repo)

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

        Ejemplos de `action` soportados (se puede extender sin romper contratos):

        - "token.info"
        - "employees.list"

        - "work_entries.list"
        - "work_entries.create"
        - "work_entries.update"
        - "work_entries.delete"
        - "work_entries.clock_in"
        - "work_entries.clock_out"

        - "time_entries.list"

        - "day_off.absences.range_all_employees"
        - "day_off.vacations.range_all_employees"

        - "worked_hours.range_all_employees"
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
        # SecurityUseCases.show_token_info ya devuelve un dict
        return self._sec_uc.show_token_info()

    # 2) Employees
    def _action_employees_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entrada JSON:
          {
            "only_active": true/false/null,   # opcional
            "page_size": 200                  # opcional, chunk de paginación interna
          }

        Salida:
          {
            "data": [ { ...employee... }, ... ],
            "meta": { "count": N }
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
        """
        Entrada JSON mínima:
          {
            "employee_id": "uuid",
            "date_from": "YYYY-MM-DD",
            "date_to":   "YYYY-MM-DD",
            "page_size": 200,           # opcional
            "all_pages": true/false,    # opcional, por defecto true
            "order_by": "workEntryIn.date asc"  # opcional
          }

        Si all_pages=true → itera paginación hasta consumir todo.
        Si all_pages=false → hace solo una llamada (puedes pasar "page").
        """
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
        """
        Entrada JSON (normalizeamos a algo estable para ti):

          {
            "employee_id": "uuid",                      # obligatorio
            "work_entry_type": "work" | "break" | ...  # opcional
            "work_check_type_id": "uuid",              # opcional
            "work_break_id": "uuid",                   # opcional

            "in": {                                    # opcional
              "at": "2025-09-01T08:00:00+02:00",
              "latitude": 40.4167,
              "longitude": -3.70325,
              "office_id": "office-uuid"
            },
            "out": {                                   # opcional
              "at": "2025-09-01T16:00:00+02:00",
              "latitude": 40.4167,
              "longitude": -3.70325,
              "office_id": "office-uuid"
            }
          }

        Salida:
          { "data": { ...work_entry... } }
        """
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
        """
        Entrada:

          {
            "work_entry_id": "uuid",                # obligatorio
            "work_entry_type": "work" | "break"...  # opcional

            "in": {                                 # opcional
              "at": "ISO",
              "latitude": float,
              "longitude": float,
              "office_id": "uuid"
            },
            "out": {                                # opcional
              "at": "ISO",
              "latitude": float,
              "longitude": float,
              "office_id": "uuid"
            }
          }
        """
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
        """
        Entrada:
          { "work_entry_id": "uuid" }
        """
        work_entry_id = self._required(payload, "work_entry_id")
        self._repo.delete_work_entry(work_entry_id=work_entry_id)
        # Si no lanza excepción, consideramos éxito.
        return {"ok": True, "work_entry_id": work_entry_id}

    # 7) Work entries: CLOCK-IN
    def _action_work_entries_clock_in(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entrada:

          {
            "employee_id": "uuid",
            "coordinates": {
              "latitude": float,
              "longitude": float
            },
            "work_check_type_id": "uuid",    # opcional
            "work_break_id": "uuid"          # opcional
          }
        """
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
        """
        Entrada:

          {
            "employee_id": "uuid",
            "coordinates": {
              "latitude": float,
              "longitude": float
            }
          }
        """
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
        """
        Entrada:

          {
            "employee_id": "uuid|null",     # opcional
            "date_from": "YYYY-MM-DD",      # opcional
            "date_to": "YYYY-MM-DD",        # opcional
            "employee_status": "active",    # opcional (por defecto 'active')
            "page": 1,
            "page_size": 200,
            "all_pages": true/false
          }
        """
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

        # Traer todo
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

    # 10) Day Offs: AUSENCIAS (todos los empleados activos en rango)
    def _action_absences_range_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entrada:

          {
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD"
          }
        """
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

    # 11) Day Offs: VACACIONES (todos los empleados activos en rango)
    def _action_vacations_range_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entrada:

          {
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD"
          }
        """
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
        """
        Entrada:

          {
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD",
            "with_checks": false   # opcional
          }
        """
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

    def _action_work_entries_status_today_all_employees(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve, para una fecha (por defecto hoy), los empleados activos
        que tienen fichajes abiertos/cerrados.

        Estructura de salida:
        {
          "data": {
            "open": [
              {
                "employee_id": "...",
                "employee_name": "...",
                "email": "...",
                "last_in_at": "...",
                "last_in_office_id": "..."
              },
              ...
            ],
            "closed": [
              {
                "employee_id": "...",
                "employee_name": "...",
                "email": "...",
                "in_at": "...",
                "out_at": "...",
                "in_office_id": "...",
                "out_office_id": "..."
              },
              ...
            ],
            "no_entries": [
              { "employee_id": "...", "employee_name": "...", "email": "..." },
              ...
            ]
          },
          "meta": { ... }
        }
        """
        # Fecha objetivo (YYYY-MM-DD). Si no viene, usamos hoy.
        date_str: str | None = payload.get("date")
        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = date.today()
            date_str = target_date.isoformat()

        # 1) empleados activos
        employees = self._emp_uc.list_employees(only_active=True, page_size=200)

        open_list: List[Dict[str, Any]] = []
        closed_list: List[Dict[str, Any]] = []
        no_entries_list: List[Dict[str, Any]] = []

        PAGE_SIZE = 100

        for emp in employees:
            if not emp.id:
                continue

            emp_name = " ".join(filter(None, [emp.first_name, emp.last_name])) or None
            base_info: Dict[str, Any] = {
                "employee_id": emp.id,
                "employee_name": emp_name,
                "email": emp.email,
            }

            # 2) fichajes del empleado para ese día (todas las páginas)
            entries: List[Any] = []
            page_num = 1
            while True:
                chunk = self._repo.list_work_entries(
                    employee_id=emp.id,
                    date_from=date_str,
                    date_to=date_str,
                    page=page_num,
                    page_size=PAGE_SIZE,
                    order_by="workEntryIn.date asc",
                )
                if not chunk:
                    break
                entries.extend(chunk)
                if len(chunk) < PAGE_SIZE:
                    break
                page_num += 1

            if not entries:
                no_entries_list.append(base_info)
                continue

            # Ordenamos por in_at/out_at para tomar el último fichaje del día
            def entry_key(we: Any) -> tuple[datetime, datetime]:
                in_at = we.in_at if isinstance(we.in_at, datetime) else datetime.min
                out_at = we.out_at if isinstance(we.out_at, datetime) else datetime.min
                return (in_at, out_at)

            try:
                entries_sorted = sorted(entries, key=entry_key)
            except Exception:
                entries_sorted = entries

            last_entry = entries_sorted[-1]

            # Abierto: tiene in_at y NO tiene out_at
            is_open = (last_entry.in_at is not None) and (last_entry.out_at is None)

            # Cerrado: al menos un entry con in_at y out_at
            last_closed_entry: Any | None = None
            for we in reversed(entries_sorted):
                if we.in_at is not None and we.out_at is not None:
                    last_closed_entry = we
                    break

            if is_open:
                open_list.append(
                    {
                        **base_info,
                        "last_in_at": last_entry.in_at,
                        "last_in_office_id": last_entry.in_office_id,
                    }
                )

            if last_closed_entry is not None:
                closed_list.append(
                    {
                        **base_info,
                        "in_at": last_closed_entry.in_at,
                        "out_at": last_closed_entry.out_at,
                        "in_office_id": last_closed_entry.in_office_id,
                        "out_office_id": last_closed_entry.out_office_id,
                    }
                )

        return {
            "data": {
                "open": open_list,
                "closed": closed_list,
                "no_entries": no_entries_list,
            },
            "meta": {
                "date": date_str,
                "active_employees": len(employees),
                "open_count": len(open_list),
                "closed_count": len(closed_list),
                "no_entries_count": len(no_entries_list),
            },
        }

