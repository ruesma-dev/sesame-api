# infrastructure/repositories/sesame_repository.py
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

from requests import Response
from tenacity import retry, stop_after_attempt, wait_exponential

from application.interfaces.sesame_port import SesamePort
from config.settings import Settings
from domain.models.employee import Employee
from domain.models.token_info import TokenInfo, CompanyInfo
from domain.models.time_entry import TimeEntry
from domain.models.work_entry import WorkEntry
from domain.models.hours_bag_history import HoursBagHistory
from infrastructure.http.http_client import HttpClient


class SesameRepositoryImpl(SesamePort):
    """Adaptador HTTP a la API de Sesame (Core v3 + Project v1 + Schedule v1)."""

    def __init__(self, settings: Settings, http: HttpClient) -> None:
        self._settings = settings
        self._http = http
        self._logger = logging.getLogger(self.__class__.__name__)

        endpoints = settings.endpoints.get("sesame", {})
        # Company / Employees
        self._token_info_path: str = endpoints.get("token_info", "/core/v3/info")
        self._employees_list_path: str = endpoints.get("employees_list", "/core/v3/employees")
        self._employees_create_path: str = endpoints.get("employees_create", "/core/v3/employees")
        # Time entries
        self._time_entries_list_path: str = endpoints.get("time_entries_list", "/project/v1/time-entries")
        # Work entries
        self._work_entries_list_path: str = endpoints.get("work_entries_list", "/schedule/v1/work-entries")
        self._work_entries_create_path: str = endpoints.get("work_entries_create", "/schedule/v1/work-entries")
        self._work_entries_update_tmpl: str = endpoints.get("work_entries_update", "/schedule/v1/work-entries/{id}")
        self._work_entries_delete_tmpl: str = endpoints.get("work_entries_delete", "/schedule/v1/work-entries/{id}")
        self._work_entries_clock_in_path: str = endpoints.get(
            "work_entries_clock_in", "/schedule/v1/work-entries/clock-in"
        )
        self._work_entries_clock_out_path: str = endpoints.get(
            "work_entries_clock_out", "/schedule/v1/work-entries/clock-out"
        )
        # Hours bag
        self._hours_bag_rule_history_list_path: str = endpoints.get(
            "hours_bag_rule_history_list", "/schedule/v1/hours-bag-rule-history"
        )

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────
    def _parse_json_or_raise(self, resp: Response, ctx: str) -> Dict[str, Any]:
        status = resp.status_code
        ctype = resp.headers.get("Content-Type", "")
        text_snippet = (resp.text or "")[:400]

        if status == 401:
            raise RuntimeError(f"{ctx}: 401 Unauthorized. Revisa token/esquema de auth.")
        if status == 204:
            return {}

        try:
            return resp.json()
        except Exception:
            raise RuntimeError(
                f"{ctx}: respuesta no-JSON. status={status} content-type={ctype} "
                f"base_url={self._http.base_url} path={resp.request.path_url} "
                f"body_snippet={text_snippet!r}"
            ) from None

    @staticmethod
    def _extract_items_list(body: Dict[str, Any], *, ctx: str) -> List[Dict[str, Any]]:
        """Normaliza contenedores tipo {'data': [...]} o variantes."""
        data = body.get("data", body)

        if isinstance(data, list):
            return [x if isinstance(x, dict) else {"raw": x} for x in data]

        if isinstance(data, dict):
            for key in ("items", "results", "entries", "list", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    return [x if isinstance(x, dict) else {"raw": x} for x in val]
            if data and all(isinstance(v, dict) for v in data.values()):
                return list(data.values())
            if any(k in data for k in ("id", "employee", "timeEntryIn", "workEntryIn")):
                return [data]

            keys = list(data.keys())
            preview = json.dumps({k: data[k] for k in keys[:5]}, ensure_ascii=False, default=str)
            raise RuntimeError(f"{ctx}: no se encontró lista de items. Claves={keys[:10]} preview={preview}")

        raise RuntimeError(f"{ctx}: estructura inesperada. type(data)={type(data)} value={str(data)[:200]}")

    # ─────────────────────────────────────────────────────────────
    # Security / Company
    # ─────────────────────────────────────────────────────────────
    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def get_token_info(self) -> TokenInfo:
        resp = self._http.get(self._token_info_path)
        body = self._parse_json_or_raise(resp, "token_info")

        data = body.get("data") or body
        company = data.get("company") or {}
        return TokenInfo(
            company=CompanyInfo(
                id=str(company.get("id", "")),
                name=company.get("name"),
                notification_email=company.get("notificationEmail") or company.get("notification_email"),
                language=company.get("language"),
                created_at=company.get("createdAt") or company.get("created_at"),
                updated_at=company.get("UpdatedAt") or company.get("updatedAt") or company.get("updated_at"),
            )
        )

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def get_token_info_raw(self) -> Dict[str, Any]:
        """Smoketest: devuelve el cuerpo JSON RAW de /core/v3/info."""
        resp = self._http.get(self._token_info_path)
        return self._parse_json_or_raise(resp, "token_info_raw")

    # ─────────────────────────────────────────────────────────────
    # Employees
    # ─────────────────────────────────────────────────────────────
    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def list_employees(
        self,
        *,
        only_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> List[Employee]:
        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if only_active is True:
            params["status[in]"] = "active"
        elif only_active is False:
            params["status[in]"] = "inactive"

        resp = self._http.get(self._employees_list_path, params=params)
        body = self._parse_json_or_raise(resp, "list_employees")

        items_raw = self._extract_items_list(body, ctx="list_employees")
        employees: List[Employee] = [self._to_domain_employee(it) for it in items_raw]
        return employees

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def create_employee(self, employee: Employee) -> Employee:
        """Crea un empleado (según los campos soportados por la API)."""
        payload = self._to_wire_create(employee)
        resp = self._http.post(self._employees_create_path, json=payload)
        body = self._parse_json_or_raise(resp, "create_employee")
        container = body.get("data") or body
        created = container if isinstance(container, dict) else {}
        return self._to_domain_employee(created)

    def bulk_create_employees(self, employees: Iterable[Employee]) -> List[Employee]:
        """Crea múltiples empleados en serie (no hay endpoint bulk documentado)."""
        return [self.create_employee(e) for e in employees]

    # ─────────────────────────────────────────────────────────────
    # Time entries  (/project/v1/time-entries)
    # ─────────────────────────────────────────────────────────────
    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def list_time_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[TimeEntry]:
        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if employee_id:
            params["employeeId"] = employee_id
        if date_from:
            params["from"] = date_from  # YYYY-MM-DD
        if date_to:
            params["to"] = date_to
        if extra_params:
            params.update(extra_params)

        resp = self._http.get(self._time_entries_list_path, params=params)
        body = self._parse_json_or_raise(resp, "list_time_entries")
        items_raw = self._extract_items_list(body, ctx="list_time_entries")
        return [self._to_domain_time_entry(it) for it in items_raw]

    # ─────────────────────────────────────────────────────────────
    # Work entries  (/schedule/v1/work-entries)
    # ─────────────────────────────────────────────────────────────
    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def list_work_entries(
        self,
        *,
        employee_id: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
        page: int = 1,
        page_size: int = 200,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[WorkEntry]:
        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if employee_id:
            params["employeeId"] = employee_id
        if date_from:
            params["from"] = date_from  # Y-m-d
        if date_to:
            params["to"] = date_to
        if extra_params:
            params.update(extra_params)

        resp = self._http.get(self._work_entries_list_path, params=params)
        body = self._parse_json_or_raise(resp, "list_work_entries")
        items_raw = self._extract_items_list(body, ctx="list_work_entries")
        return [self._to_domain_work_entry(it) for it in items_raw]

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def create_work_entry(self, payload: Dict[str, Any]) -> WorkEntry:
        resp = self._http.post(self._work_entries_create_path, json=payload)
        body = self._parse_json_or_raise(resp, "create_work_entry")
        container = body.get("data") or body
        obj = container if isinstance(container, dict) else {}
        return self._to_domain_work_entry(obj)

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def update_work_entry(self, work_entry_id: str, payload: Dict[str, Any]) -> WorkEntry:
        path = self._work_entries_update_tmpl.format(id=work_entry_id)
        # preferimos PUT; usamos POST como fallback si el cliente no lo expone
        resp = self._http.post(path, json=payload)
        if resp.status_code in (404, 405):
            resp = self._http.session.put(
                f"{self._http.base_url}{path}",
                headers=self._http._headers(),  # type: ignore[attr-defined]
                json=payload,
                timeout=self._http.timeout_seconds,
            )
        body = self._parse_json_or_raise(resp, "update_work_entry")
        container = body.get("data") or body
        obj = container if isinstance(container, dict) else {}
        return self._to_domain_work_entry(obj)

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def delete_work_entry(self, work_entry_id: str) -> bool:
        path = self._work_entries_delete_tmpl.format(id=work_entry_id)
        resp = self._http.session.delete(
            f"{self._http.base_url}{path}",
            headers=self._http._headers(),  # type: ignore[attr-defined]
            timeout=self._http.timeout_seconds,
        )
        if resp.status_code in (200, 204):
            return True
        body = self._parse_json_or_raise(resp, "delete_work_entry")
        return bool(body)

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def clock_in(
        self,
        *,
        employee_id: str,
        coordinates: Optional[Dict[str, float]] = None,
        work_check_type_id: Optional[str] = None,
        work_break_id: Optional[str] = None,
    ) -> WorkEntry:
        payload: Dict[str, Any] = {"employeeId": employee_id}
        if coordinates:
            payload["workEntryIn"] = {"coordinates": coordinates}
        if work_check_type_id:
            payload["workCheckTypeId"] = work_check_type_id
        if work_break_id:
            payload["workBreakId"] = work_break_id

        resp = self._http.post(self._work_entries_clock_in_path, json=payload)
        body = self._parse_json_or_raise(resp, "clock_in")
        container = body.get("data") or body
        obj = container if isinstance(container, dict) else {}
        return self._to_domain_work_entry(obj)

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def clock_out(
        self,
        *,
        employee_id: str,
        coordinates: Optional[Dict[str, float]] = None,
    ) -> WorkEntry:
        payload: Dict[str, Any] = {"employeeId": employee_id}
        if coordinates:
            payload["workEntryOut"] = {"coordinates": coordinates}

        resp = self._http.post(self._work_entries_clock_out_path, json=payload)
        body = self._parse_json_or_raise(resp, "clock_out")
        container = body.get("data") or body
        obj = container if isinstance(container, dict) else {}
        return self._to_domain_work_entry(obj)

    # ─────────────────────────────────────────────────────────────
    # Hours bag (bolsa de horas)
    # ─────────────────────────────────────────────────────────────
    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def list_hours_bag_rule_history(
        self,
        *,
        date_from: Optional[str],
        date_to: Optional[str],
        employee_ids: Optional[List[str]] = None,
        hours_bag_rule_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[HoursBagHistory]:
        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        if employee_ids:
            params["employeeIds"] = employee_ids  # repeated param
        if hours_bag_rule_ids:
            params["hoursBagRuleIds"] = hours_bag_rule_ids

        resp = self._http.get(self._hours_bag_rule_history_list_path, params=params)
        body = self._parse_json_or_raise(resp, "list_hours_bag_rule_history")
        items_raw = self._extract_items_list(body, ctx="list_hours_bag_rule_history")
        return [self._to_domain_hours_bag_history(it) for it in items_raw]

    # ─────────────────────────────────────────────────────────────
    # Mapeos
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _to_domain_employee(obj: Dict[str, Any]) -> Employee:
        from domain.models.employee import Employee as EmployeeModel
        company = obj.get("company") or {}
        return EmployeeModel(
            id=str(obj.get("id") or ""),
            first_name=obj.get("firstName") or obj.get("first_name") or "",
            last_name=obj.get("lastName") or obj.get("last_name") or "",
            email=obj.get("email"),
            personal_mail=obj.get("personalMail"),
            work_status=obj.get("workStatus"),
            image_profile_url=obj.get("imageProfileURL"),
            code=obj.get("code"),
            pin=obj.get("pin"),
            phone=obj.get("phone"),
            work_phone=obj.get("workPhone"),
            company_id=company.get("id"),
            company_name=company.get("name"),
            company_notification_email=company.get("notificationEmail"),
            company_language=company.get("language"),
            company_created_at=company.get("createdAt"),
            company_updated_at=company.get("UpdatedAt") or company.get("updatedAt"),
            gender=obj.get("gender"),
            contract_id=obj.get("contractId"),
            nid=obj.get("nid"),
            identity_number_type=obj.get("identityNumberType"),
            ssn=obj.get("ssn"),
            price_per_hour=obj.get("pricePerHour"),
            account_number=obj.get("accountNumber"),
            date_of_birth=obj.get("dateOfBirth"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("UpdatedAt") or obj.get("updatedAt"),
            status=obj.get("status"),
            children=obj.get("children"),
            disability=obj.get("disability"),
            address=obj.get("address"),
            postal_code=obj.get("postalCode"),
            city=obj.get("city"),
            province=obj.get("province"),
            country=obj.get("country"),
            nationality=obj.get("nationality"),
            nationalities=obj.get("nationalities"),
            marital_status=obj.get("maritalStatus"),
            emergency_phone=obj.get("emergencyPhone"),
            description=obj.get("description"),
            salary_range=obj.get("salaryRange"),
            study_level=obj.get("studyLevel"),
            professional_category_code=obj.get("professionalCategoryCode"),
            professional_category_description=obj.get("professionalCategoryDescription"),
            bic=obj.get("bic"),
            job_charge_id=obj.get("jobChargeId"),
            job_charge_name=obj.get("jobChargeName"),
            language=obj.get("language"),
            nfc=obj.get("nfc"),
            main_recruiter_id=(obj.get("mainRecruiter") or {}).get("id")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_first_name=(obj.get("mainRecruiter") or {}).get("firstName")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_last_name=(obj.get("mainRecruiter") or {}).get("lastName")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_image_profile_url=(obj.get("mainRecruiter") or {}).get("imageProfileURL")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_email=(obj.get("mainRecruiter") or {}).get("email")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_work_status=(obj.get("mainRecruiter") or {}).get("workStatus")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_work_check_type_color=(obj.get("mainRecruiter") or {}).get("workCheckTypeColor")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            main_recruiter_work_check_type_name=(obj.get("mainRecruiter") or {}).get("workCheckTypeName")
            if isinstance(obj.get("mainRecruiter"), dict)
            else None,
            custom_fields=obj.get("customFields"),
        )

    @staticmethod
    def _to_domain_time_entry(obj: Dict[str, Any]) -> TimeEntry:
        emp = obj.get("employee") or {}
        tin = obj.get("timeEntryIn") or {}
        tout = obj.get("timeEntryOut") or {}
        cin = tin.get("coordinates") or {}
        cout = tout.get("coordinates") or {}
        return TimeEntry(
            id=str(obj.get("id") or ""),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            project_id=obj.get("projectId"),
            tag_ids=obj.get("tagIds"),
            in_at=tin.get("date"),
            in_latitude=cin.get("latitude"),
            in_longitude=cin.get("longitude"),
            out_at=tout.get("date"),
            out_latitude=cout.get("latitude"),
            out_longitude=cout.get("longitude"),
            comment=obj.get("comment"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("UpdatedAt") or obj.get("updatedAt"),
            deleted_at=obj.get("deletedAt"),
            raw=obj,
        )

    @staticmethod
    def _to_domain_work_entry(obj: Dict[str, Any]) -> WorkEntry:
        emp = obj.get("employee") or {}
        win = obj.get("workEntryIn") or {}
        wout = obj.get("workEntryOut") or {}
        cin = win.get("coordinates") or {}
        cout = wout.get("coordinates") or {}
        return WorkEntry(
            id=str(obj.get("id") or ""),
            work_check_type_id=obj.get("workCheckTypeId"),
            work_entry_type=obj.get("workEntryType"),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            in_origin=win.get("origin"),
            in_at=win.get("date"),
            in_latitude=cin.get("latitude"),
            in_longitude=cin.get("longitude"),
            in_office_id=win.get("officeId"),
            out_origin=wout.get("origin"),
            out_at=wout.get("date"),
            out_latitude=cout.get("latitude"),
            out_longitude=cout.get("longitude"),
            out_office_id=wout.get("officeId"),
            worked_seconds=obj.get("workedSeconds"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("UpdatedAt") or obj.get("updatedAt"),
            deleted_at=obj.get("deletedAt"),
            raw=obj,
        )

    @staticmethod
    def _to_domain_hours_bag_history(obj: Dict[str, Any]) -> HoursBagHistory:
        rule = obj.get("hoursBagRule") or {}
        emp = obj.get("employee") or {}
        return HoursBagHistory(
            id=str(obj.get("id") or ""),
            date=obj.get("date"),
            seconds=obj.get("seconds"),
            check_seconds=obj.get("checkSeconds"),
            check_seconds_with_variation=obj.get("checkSecondsWithVariation"),
            hours_bag_rule_id=rule.get("id"),
            hours_bag_rule_name=rule.get("name"),
            hours_bag_rule_variation=rule.get("variation"),
            employee_id=emp.get("id"),
            employee_name=emp.get("name"),
            raw=obj,
        )

    @staticmethod
    def _to_wire_create(emp: Employee) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "firstName": emp.first_name,
            "lastName": emp.last_name,
        }
        if emp.email:
            payload["email"] = str(emp.email)
        if emp.phone:
            payload["phone"] = emp.phone
        if emp.code is not None:
            payload["code"] = emp.code
        if emp.pin is not None:
            payload["pin"] = emp.pin
        if emp.date_of_birth:
            payload["dateOfBirth"] = str(emp.date_of_birth)
        if emp.gender:
            payload["gender"] = emp.gender
        return payload
