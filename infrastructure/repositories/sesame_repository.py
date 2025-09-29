# infrastructure/repositories/sesame_repository.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import Settings
from infrastructure.http.http_client import HttpClient

# Domain models
from domain.models.employee import Employee as EmployeeModel
from domain.models.work_entry import WorkEntry as WorkEntryModel
from domain.models.time_entry import TimeEntry as TimeEntryModel
from domain.models.hours_bag_history import HoursBagHistory as HoursBagHistoryModel
from domain.models.employee_office_assignation import (
    EmployeeOfficeAssignation as EmployeeOfficeAssignationModel,
)
from domain.models.office import Office as OfficeModel

# Puerto (interfaz) de aplicación
from application.interfaces.sesame_port import SesamePort


SAFE_LIMIT_DEFAULT = 100


class SesameRepositoryImpl(SesamePort):
    def __init__(self, settings: Settings, http: HttpClient, *, endpoints: Dict[str, str]) -> None:
        self._settings = settings
        self._http = http
        self._ep: Dict[str, str] = endpoints
        self._log = logging.getLogger(self.__class__.__name__)

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _safe_limit(limit: Optional[int]) -> int:
        try:
            if limit is None:
                return SAFE_LIMIT_DEFAULT
            return min(int(limit), SAFE_LIMIT_DEFAULT)
        except Exception:
            return SAFE_LIMIT_DEFAULT

    def _parse_json_or_raise(self, resp: requests.Response, msg: str) -> Dict[str, Any]:
        ctype = resp.headers.get("Content-Type", "")
        try:
            body = resp.json()
        except Exception:
            text_snippet = (resp.text or "")[:300]
            raise RuntimeError(
                f"{msg}: respuesta no-JSON. status={resp.status_code} content-type={ctype} "
                f"base_url={self._http.base_url} path={getattr(resp.request, 'path_url', '')} "
                f"body_snippet={text_snippet!r}"
            )
        if not (200 <= resp.status_code < 300):
            emsg = None
            if isinstance(body, dict):
                err = body.get("error") or {}
                if isinstance(err, dict):
                    emsg = err.get("message") or err.get("errors") or "Unknown error"
                else:
                    emsg = str(err)
            raise RuntimeError(
                f"{msg}: HTTP {resp.status_code}. base_url={self._http.base_url} path={getattr(resp.request, 'path_url', '')} "
                f"content-type={ctype} body_snippet={str(body)[:300]!r}"
            )
        return body if isinstance(body, dict) else {"data": body}

    @staticmethod
    def _get_data_list(body: Dict[str, Any]) -> List[Any]:
        data = body.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []

    # ─────────────────────────────────────────────────────────────
    # Token / Company
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def get_token_info_raw(self) -> Dict[str, Any]:
        path = self._ep["token_info"]
        resp = self._http.get(path)
        return self._parse_json_or_raise(resp, "token_info_raw")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def get_token_info(self) -> Dict[str, Any]:
        body = self.get_token_info_raw()
        company = ((body.get("data") or {}).get("company") or {}) if isinstance(body, dict) else {}
        parsed_company = {
            "id": company.get("id"),
            "name": company.get("name"),
            "language": company.get("language"),
            "notificationEmail": company.get("notificationEmail"),
        }
        token = self._http.token
        token_masked = f"{token[:6]}...{token[-6:]}" if isinstance(token, str) and len(token) > 12 else "******"
        return {
            "base_url": self._http.base_url,
            "auth_scheme": self._http.auth_scheme,
            "token_masked": token_masked,
            "parsed_company": parsed_company,
            "raw_response": body,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def get_company(self) -> Dict[str, Any]:
        info = self.get_token_info()
        return info.get("parsed_company") or {}

    # ─────────────────────────────────────────────────────────────
    # Employees
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def list_employees(self, *, only_active: bool = True, page: int = 1, page_size: int = 100) -> List[EmployeeModel]:
        path = self._ep["employees_list"]
        params: Dict[str, Any] = {
            "page": page,
            "limit": self._safe_limit(page_size),
        }
        if only_active:
            # Operador "in" documentado por Sesame
            params["status[in]"] = "active"

        resp = self._http.get(path, params=params)
        body = self._parse_json_or_raise(resp, "list_employees")
        items_raw = self._get_data_list(body)
        return [self._to_domain_employee(it) for it in items_raw if isinstance(it, dict)]

    # Opcionales (no obligatorios por el ABC actual, mantenemos placeholders)
    def create_employee(self, employee: EmployeeModel) -> EmployeeModel:  # pragma: no cover
        raise NotImplementedError("create_employee no implementado en este microservicio.")

    def bulk_create_employees(self, employees: Sequence[EmployeeModel]) -> List[EmployeeModel]:  # pragma: no cover
        raise NotImplementedError("bulk_create_employees no implementado en este microservicio.")

    # ─────────────────────────────────────────────────────────────
    # Work Entries (LECTURA)
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def list_work_entries(
        self,
        *,
        employee_id: str,
        date_from: str,
        date_to: str,
        page: int = 1,
        page_size: int = 100,
        order_by: Optional[str] = None,
    ) -> List[WorkEntryModel]:
        path = self._ep["work_entries_list"]
        params: Dict[str, Any] = {
            "page": page,
            "limit": self._safe_limit(page_size),
            "employeeId": employee_id,
            "from": date_from,
            "to": date_to,
        }
        if order_by:
            params["orderBy"] = order_by

        resp = self._http.get(path, params=params)
        body = self._parse_json_or_raise(resp, "list_work_entries")
        items_raw = self._get_data_list(body)
        return [self._to_domain_work_entry(it) for it in items_raw if isinstance(it, dict)]

    # ─────────────────────────────────────────────────────────────
    # Work Entries (ESCRITURA)
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def create_work_entry(
        self,
        *,
        employee_id: str,
        in_at: Optional[str] = None,
        out_at: Optional[str] = None,
        work_entry_type: Optional[str] = "work",
        work_check_type_id: Optional[str] = None,
        work_break_id: Optional[str] = None,
        in_latitude: Optional[float] = None,
        in_longitude: Optional[float] = None,
        out_latitude: Optional[float] = None,
        out_longitude: Optional[float] = None,
        in_office_id: Optional[str] = None,
        out_office_id: Optional[str] = None,
    ) -> WorkEntryModel:
        path = self._ep["work_entries_create"]

        payload: Dict[str, Any] = {
            "employeeId": employee_id,
        }
        if work_entry_type:
            payload["workEntryType"] = work_entry_type
        if work_check_type_id:
            payload["workCheckTypeId"] = work_check_type_id
        if work_break_id:
            payload["workBreakId"] = work_break_id

        if in_at:
            entry_in: Dict[str, Any] = {"date": in_at}
            coords: Dict[str, Any] = {}
            if in_latitude is not None:
                coords["latitude"] = in_latitude
            if in_longitude is not None:
                coords["longitude"] = in_longitude
            if coords:
                entry_in["coordinates"] = coords
            if in_office_id:
                entry_in["officeId"] = in_office_id
            payload["workEntryIn"] = entry_in

        if out_at:
            entry_out: Dict[str, Any] = {"date": out_at}
            coords_o: Dict[str, Any] = {}
            if out_latitude is not None:
                coords_o["latitude"] = out_latitude
            if out_longitude is not None:
                coords_o["longitude"] = out_longitude
            if coords_o:
                entry_out["coordinates"] = coords_o
            if out_office_id:
                entry_out["officeId"] = out_office_id
            payload["workEntryOut"] = entry_out

        resp = self._http.post(path, json=payload)
        body = self._parse_json_or_raise(resp, "create_work_entry")
        data = (body.get("data") or {}) if isinstance(body, dict) else {}
        return self._to_domain_work_entry(data if isinstance(data, dict) else {})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def update_work_entry(
        self,
        *,
        work_entry_id: str,
        work_entry_type: Optional[str] = None,
        in_at: Optional[str] = None,
        out_at: Optional[str] = None,
        in_latitude: Optional[float] = None,
        in_longitude: Optional[float] = None,
        out_latitude: Optional[float] = None,
        out_longitude: Optional[float] = None,
        in_office_id: Optional[str] = None,
        out_office_id: Optional[str] = None,
    ) -> WorkEntryModel:
        path = self._ep["work_entries_update"].replace("{id}", work_entry_id)

        payload: Dict[str, Any] = {}
        if work_entry_type:
            payload["workEntryType"] = work_entry_type

        if in_at or in_latitude is not None or in_longitude is not None or in_office_id:
            entry_in: Dict[str, Any] = {}
            if in_at:
                entry_in["date"] = in_at
            coords: Dict[str, Any] = {}
            if in_latitude is not None:
                coords["latitude"] = in_latitude
            if in_longitude is not None:
                coords["longitude"] = out_longitude if out_longitude is not None else in_longitude
            if coords:
                entry_in["coordinates"] = coords
            if in_office_id:
                entry_in["officeId"] = in_office_id
            payload["workEntryIn"] = entry_in

        if out_at or out_latitude is not None or out_longitude is not None or out_office_id:
            entry_out: Dict[str, Any] = {}
            if out_at:
                entry_out["date"] = out_at
            coords_o: Dict[str, Any] = {}
            if out_latitude is not None:
                coords_o["latitude"] = out_latitude
            if out_longitude is not None:
                coords_o["longitude"] = out_longitude
            if coords_o:
                entry_out["coordinates"] = coords_o
            if out_office_id:
                entry_out["officeId"] = out_office_id
            payload["workEntryOut"] = entry_out

        resp = self._http.put(path, json=payload)
        body = self._parse_json_or_raise(resp, "update_work_entry")
        data = (body.get("data") or {}) if isinstance(body, dict) else {}
        return self._to_domain_work_entry(data if isinstance(data, dict) else {})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def delete_work_entry(self, *, work_entry_id: str) -> None:
        path = self._ep["work_entries_delete"].replace("{id}", work_entry_id)
        resp = self._http.delete(path)
        # Si no 2xx lanza error dentro de _parse_json_or_raise
        self._parse_json_or_raise(resp, "delete_work_entry")

    # Clock in/out
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def clock_in(
        self,
        *,
        employee_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        work_check_type_id: Optional[str] = None,
        work_break_id: Optional[str] = None,
    ) -> WorkEntryModel:
        path = self._ep["work_entries_clock_in"]
        payload: Dict[str, Any] = {"employeeId": employee_id}
        entry_in: Dict[str, Any] = {}
        coords: Dict[str, Any] = {}
        if latitude is not None:
            coords["latitude"] = latitude
        if longitude is not None:
            coords["longitude"] = longitude
        if coords:
            entry_in["coordinates"] = coords
        if entry_in:
            payload["workEntryIn"] = entry_in
        if work_check_type_id:
            payload["workCheckTypeId"] = work_check_type_id
        if work_break_id:
            payload["workBreakId"] = work_break_id

        resp = self._http.post(path, json=payload)
        body = self._parse_json_or_raise(resp, "clock_in")
        data = (body.get("data") or {}) if isinstance(body, dict) else {}
        return self._to_domain_work_entry(data if isinstance(data, dict) else {})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def clock_out(
        self,
        *,
        employee_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> WorkEntryModel:
        path = self._ep["work_entries_clock_out"]
        payload: Dict[str, Any] = {"employeeId": employee_id}
        entry_out: Dict[str, Any] = {}
        coords: Dict[str, Any] = {}
        if latitude is not None:
            coords["latitude"] = latitude
        if longitude is not None:
            coords["longitude"] = longitude
        if coords:
            entry_out["coordinates"] = coords
        if entry_out:
            payload["workEntryOut"] = entry_out

        resp = self._http.post(path, json=payload)
        body = self._parse_json_or_raise(resp, "clock_out")
        data = (body.get("data") or {}) if isinstance(body, dict) else {}
        return self._to_domain_work_entry(data if isinstance(data, dict) else {})

    # ─────────────────────────────────────────────────────────────
    # Time Entries (proyectos)
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def list_time_entries(
        self,
        *,
        employee_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        employee_status: Optional[str] = "active",
        page: int = 1,
        page_size: int = 100,
    ) -> List[TimeEntryModel]:
        path = self._ep["time_entries_list"]
        params: Dict[str, Any] = {
            "page": page,
            "limit": self._safe_limit(page_size),
        }
        if employee_id:
            params["employeeId"] = employee_id
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        if employee_status:
            params["employeeStatus"] = employee_status

        resp = self._http.get(path, params=params)
        body = self._parse_json_or_raise(resp, "list_time_entries")
        items_raw = self._get_data_list(body)
        return [self._to_domain_time_entry(it) for it in items_raw if isinstance(it, dict)]

    # ─────────────────────────────────────────────────────────────
    # Hours Bag Rule History
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def list_hours_bag_rule_history(
        self,
        *,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        employee_ids: Optional[Sequence[str]] = None,
        hours_bag_rule_ids: Optional[Sequence[str]] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> List[HoursBagHistoryModel]:
        path = self._ep["hours_bag_rule_history_list"]
        params: Dict[str, Any] = {
            "page": page,
            "limit": self._safe_limit(page_size),
        }
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to

        # En Swagger aceptan repetir employeeIds=... varias veces; requests lo hace si pasamos list
        if employee_ids:
            params["employeeIds"] = list(employee_ids)

        # hoursBagRuleIds es opcional; si no se conoce, mejor no enviarlo
        if hours_bag_rule_ids:
            params["hoursBagRuleIds"] = list(hours_bag_rule_ids)

        resp = self._http.get(path, params=params)
        body = self._parse_json_or_raise(resp, "list_hours_bag_rule_history")
        items_raw = self._get_data_list(body)
        return [self._to_domain_hours_bag_history(it) for it in items_raw if isinstance(it, dict)]

    # ─────────────────────────────────────────────────────────────
    # Employee–Office assignations
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def list_employee_office_assignations(
        self,
        *,
        employee_id: Optional[str] = None,
        office_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> List[EmployeeOfficeAssignationModel]:
        path = self._ep["employee_office_assignations_list"]
        params: Dict[str, Any] = {"page": page, "limit": self._safe_limit(page_size)}
        if employee_id:
            params["employeeId"] = employee_id
        if office_id:
            params["officeId"] = office_id

        resp = self._http.get(path, params=params)
        body = self._parse_json_or_raise(resp, "list_employee_office_assignations")
        items_raw = self._get_data_list(body)
        return [self._to_domain_employee_office_assignation(it) for it in items_raw if isinstance(it, dict)]

    # ─────────────────────────────────────────────────────────────
    # Offices
    # ─────────────────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=2), reraise=True,
           retry=retry_if_exception_type((requests.RequestException, RuntimeError)))
    def list_offices(self, *, name: Optional[str] = None, page: int = 1, page_size: int = 100) -> List[OfficeModel]:
        path = self._ep["offices_list"]
        params: Dict[str, Any] = {"page": page, "limit": self._safe_limit(page_size)}
        if name:
            params["name"] = name
        resp = self._http.get(path, params=params)
        body = self._parse_json_or_raise(resp, "list_offices")
        items_raw = self._get_data_list(body)
        return [self._to_domain_office(it) for it in items_raw if isinstance(it, dict)]

    # ─────────────────────────────────────────────────────────────
    # Mapeos
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _to_domain_employee(obj: Dict[str, Any]) -> EmployeeModel:
        first_name = obj.get("firstName") or ""
        last_name = obj.get("lastName") or ""
        email = obj.get("email") or obj.get("personalMail") or None
        status = obj.get("status") or None
        code = obj.get("code")
        code_str = str(code) if code is not None else None

        return EmployeeModel(
            id=str(obj.get("id") or obj.get("_id") or obj.get("uuid") or ""),
            first_name=first_name,
            last_name=last_name,
            email=email,
            status=status,
            code=code_str,
        )

    @staticmethod
    def _to_domain_work_entry(obj: Dict[str, Any]) -> WorkEntryModel:
        emp = obj.get("employee") or {}
        win = obj.get("workEntryIn") or {}
        wout = obj.get("workEntryOut") or {}

        coords_in = (win.get("coordinates") or {})
        coords_out = (wout.get("coordinates") or {})

        return WorkEntryModel(
            id=str(obj.get("id") or ""),
            work_check_type_id=obj.get("workCheckTypeId"),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            work_entry_type=obj.get("workEntryType"),
            in_at=win.get("date"),
            in_latitude=coords_in.get("latitude"),
            in_longitude=coords_in.get("longitude"),
            in_office_id=win.get("officeId"),
            out_at=wout.get("date"),
            out_latitude=coords_out.get("latitude"),
            out_longitude=coords_out.get("longitude"),
            out_office_id=wout.get("officeId"),
            worked_seconds=obj.get("workedSeconds"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("updatedAt"),
            deleted_at=obj.get("deletedAt"),
        )

    @staticmethod
    def _to_domain_time_entry(obj: Dict[str, Any]) -> TimeEntryModel:
        emp = obj.get("employee") or {}
        tin = obj.get("timeEntryIn") or {}
        tout = obj.get("timeEntryOut") or {}

        coords_in = (tin.get("coordinates") or {})
        coords_out = (tout.get("coordinates") or {})

        return TimeEntryModel(
            id=str(obj.get("id") or ""),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            project_id=obj.get("projectId"),
            tag_ids=obj.get("tagIds"),
            in_at=tin.get("date"),
            in_latitude=coords_in.get("latitude"),
            in_longitude=coords_in.get("longitude"),
            out_at=tout.get("date"),
            out_latitude=coords_out.get("latitude"),
            out_longitude=coords_out.get("longitude"),
            comment=obj.get("comment"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("UpdatedAt") if obj.get("UpdatedAt") else obj.get("updatedAt"),
            deleted_at=obj.get("deletedAt"),
        )

    @staticmethod
    def _to_domain_hours_bag_history(obj: Dict[str, Any]) -> HoursBagHistoryModel:
        hb = obj.get("hoursBagRule") or {}
        emp = obj.get("employee") or {}
        return HoursBagHistoryModel(
            id=str(obj.get("id") or ""),
            date=obj.get("date"),
            seconds=obj.get("seconds"),
            hours_bag_rule_id=hb.get("id"),
            hours_bag_rule_name=hb.get("name"),
            hours_bag_rule_variation=hb.get("variation"),
            employee_id=emp.get("id"),
            employee_name=emp.get("name") or " ".join(
                [x for x in [emp.get("firstName"), emp.get("lastName")] if x]
            ),
            check_seconds=obj.get("checkSeconds"),
            check_seconds_with_variation=obj.get("checkSecondsWithVariation"),
        )

    @staticmethod
    def _to_domain_employee_office_assignation(obj: Dict[str, Any]) -> EmployeeOfficeAssignationModel:
        emp = obj.get("employee") or {}
        off = obj.get("office") or {}
        coords = (off.get("coordinates") or {})
        return EmployeeOfficeAssignationModel(
            id=str(obj.get("id") or ""),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            office_id=off.get("id"),
            office_name=off.get("name"),
            office_address=off.get("address"),
            office_latitude=coords.get("latitude"),
            office_longitude=coords.get("longitude"),
            office_description=off.get("description"),
            office_radius=off.get("radio"),
            default_timezone=off.get("defaultEmployeesDateTimeZone"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("updatedAt"),
        )

    @staticmethod
    def _to_domain_office(obj: Dict[str, Any]) -> OfficeModel:
        coords = (obj.get("coordinates") or {})
        return OfficeModel(
            id=str(obj.get("id") or ""),
            name=obj.get("name"),
            address=obj.get("address"),
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
            description=obj.get("description"),
            radius=obj.get("radio"),
            default_timezone=obj.get("defaultEmployeesDateTimeZone"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("updatedAt"),
        )
