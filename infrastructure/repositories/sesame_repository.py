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
from infrastructure.http.http_client import HttpClient


class SesameRepositoryImpl(SesamePort):
    """Adaptador a la API real de Sesame (Core v3)."""

    def __init__(self, settings: Settings, http: HttpClient) -> None:
        self._settings = settings
        self._http = http
        self._logger = logging.getLogger(self.__class__.__name__)

        endpoints = settings.endpoints.get("sesame", {})
        self._token_info_path: str = endpoints.get("token_info", "/core/v3/info")
        self._employees_list_path: str = endpoints.get("employees_list", "/core/v3/employees")
        self._employees_create_path: str = endpoints.get("employees_create", "/core/v3/employees")

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────
    def _parse_json_or_raise(self, resp: Response, ctx: str) -> Dict[str, Any]:
        status = resp.status_code
        ctype = resp.headers.get("Content-Type", "")
        text_snippet = (resp.text or "")[:400]

        if status == 401:
            raise RuntimeError(f"{ctx}: 401 Unauthorized. Revisa token/esquema de auth.")
        if status == 204:
            raise RuntimeError(f"{ctx}: 204 No Content. El endpoint no devolvió body JSON.")

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
        """
        Normaliza la lista de items desde diferentes formas de payload.
        Devuelve SIEMPRE una lista de dicts.
        """
        data = body.get("data", body)

        if isinstance(data, list):
            if all(isinstance(x, dict) for x in data):
                return data
            raise RuntimeError(f"{ctx}: la lista recibida no contiene objetos. Ejemplo={data[:3]}")

        if isinstance(data, dict):
            for key in ("items", "results", "employees", "list", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    if all(isinstance(x, dict) for x in val):
                        return val
                    raise RuntimeError(
                        f"{ctx}: '{key}' no es lista de objetos. "
                        f"Tipo={type(val)} ej={val[:3] if isinstance(val, list) else val}"
                    )

            if data and all(isinstance(v, dict) for v in data.values()):
                return list(data.values())

            if any(k in data for k in ("id", "firstName", "first_name")):
                return [data]

            keys = list(data.keys())
            preview = json.dumps({k: data[k] for k in keys[:5]}, ensure_ascii=False, default=str)
            raise RuntimeError(f"{ctx}: no se encontró lista de items. Claves={keys[:10]} preview={preview}")

        raise RuntimeError(f"{ctx}: estructura inesperada. type(data)={type(data)} value={str(data)[:200]}")

    # ──────────────────────────────────────────────────────────────────────
    # Security
    # ──────────────────────────────────────────────────────────────────────
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
                updated_at=company.get("UpdatedAt") or company.get("updated_at"),
            )
        )

    # ──────────────────────────────────────────────────────────────────────
    # Employees
    # ──────────────────────────────────────────────────────────────────────
    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def list_employees(
        self,
        *,
        only_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> List[Employee]:
        """
        GET /core/v3/employees
        Soporta filtro de estado con status[in]=active,inactive.
        """
        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if only_active is True:
            params["status[in]"] = "active"
        elif only_active is False:
            params["status[in]"] = "inactive"
        # Si None → por defecto del API (solo activos).

        resp = self._http.get(self._employees_list_path, params=params)
        body = self._parse_json_or_raise(resp, "list_employees")

        items_raw = self._extract_items_list(body, ctx="list_employees")
        employees: List[Employee] = [self._to_domain_employee(it) for it in items_raw]
        return employees

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=8), stop=stop_after_attempt(3))
    def create_employee(self, employee: Employee) -> Employee:
        """
        POST /core/v3/employees (no se usa en la exportación, pero implementado para el puerto).
        """
        payload = self._to_wire_create(employee)
        resp = self._http.post(self._employees_create_path, json=payload)
        body = self._parse_json_or_raise(resp, "create_employee")

        container = body.get("data") or body
        created_obj: Dict[str, Any]
        if isinstance(container, dict) and any(k in container for k in ("id", "firstName", "first_name")):
            created_obj = container
        elif isinstance(container, dict):
            for key in ("employee", "item", "data"):
                val = container.get(key)
                if isinstance(val, dict):
                    created_obj = val
                    break
            else:
                created_obj = container
        else:
            raise RuntimeError("create_employee: estructura inesperada al crear empleado.")

        return self._to_domain_employee(created_obj)

    def bulk_create_employees(self, employees: Iterable[Employee]) -> List[Employee]:
        created: List[Employee] = []
        for emp in employees:
            created.append(self.create_employee(emp))
        return created

    # ──────────────────────────────────────────────────────────────────────
    # Mapeos
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _to_domain_employee(obj: Dict[str, Any]) -> Employee:
        company = obj.get("company") or {}
        mr = obj.get("mainRecruiter") or {}

        return Employee(
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
            company_updated_at=company.get("updatedAt"),

            gender=obj.get("gender"),
            contract_id=obj.get("contractId"),
            nid=obj.get("nid"),
            identity_number_type=obj.get("identityNumberType"),
            ssn=obj.get("ssn"),
            price_per_hour=obj.get("pricePerHour"),
            account_number=obj.get("accountNumber"),

            date_of_birth=obj.get("dateOfBirth"),
            created_at=obj.get("createdAt"),
            updated_at=obj.get("updatedAt"),

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

            main_recruiter_id=mr.get("id"),
            main_recruiter_first_name=mr.get("firstName"),
            main_recruiter_last_name=mr.get("lastName"),
            main_recruiter_image_profile_url=mr.get("imageProfileURL"),
            main_recruiter_email=mr.get("email"),
            main_recruiter_work_status=mr.get("workStatus"),
            main_recruiter_work_check_type_color=mr.get("workCheckTypeColor"),
            main_recruiter_work_check_type_name=mr.get("workCheckTypeName"),

            custom_fields=obj.get("customFields"),
        )

    @staticmethod
    def _to_wire_create(emp: Employee) -> Dict[str, Any]:
        """
        Payload mínimo seguro para v3. Ajusta si tu tenant exige más campos.
        """
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
