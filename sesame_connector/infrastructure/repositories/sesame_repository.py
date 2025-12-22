# sesame_connector/infrastructure/repositories/sesame_repository.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.errors import EndpointNotConfiguredError

from sesame_connector.domain.models.absence_day_off import AbsenceDayOff
from sesame_connector.domain.models.employee import Employee
from sesame_connector.domain.models.project import Project
from sesame_connector.domain.models.tag import Tag
from sesame_connector.domain.models.time_entry import TimeEntry
from sesame_connector.domain.models.vacation_day_off import VacationDayOff
from sesame_connector.domain.models.work_entry import WorkEntry
from sesame_connector.domain.models.worked_hours_stat import WorkedHoursStat

from sesame_connector.infrastructure.http.http_client import HttpClient



class SesameRepository(SesamePort):
    def __init__(self, *, http: HttpClient, endpoints: Dict[str, str]) -> None:
        self._http = http
        self._endpoints = endpoints

    def _ep(self, key: str) -> str:
        if key not in self._endpoints:
            raise EndpointNotConfiguredError(key=key)
        return self._endpoints[key]

    @staticmethod
    def _parse_json(resp) -> Any:
        try:
            return resp.json()
        except Exception:
            return resp.text

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        ok_status: Tuple[int, ...] = (200, 201),
    ) -> Any:
        resp = self._http.request(method, path, params=params, json_body=json_body)
        payload = self._parse_json(resp)
        if resp.status_code not in ok_status:
            raise SesameApiError(method=method.upper(), path=path, status_code=resp.status_code, body=payload)
        return payload

    # ---------------- Security / token info ----------------
    def get_token_info_raw(self) -> Dict:
        path = self._ep("token_info")
        payload = self._request_json("GET", path, ok_status=(200,))
        return payload

    # ---------------- Employees ----------------
    def list_employees(
        self,
        *,
        only_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[Employee]:
        path = self._ep("employees_list")

        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if only_active is True:
            # muchas APIs usan status=active (si tu tenant usa otro param, lo ajustamos aquí)
            params["status"] = "active"

        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", [])
        out: List[Employee] = []
        for it in data:
            out.append(self._map_employee(it))
        return out

    # ---------------- Projects ----------------
    def list_projects(self, *, page: int = 1, page_size: int = 100) -> List[Project]:
        path = self._ep("projects_list")
        params = {"page": page, "limit": page_size}
        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", [])
        return [self._map_project(it) for it in data]

    def create_project(self, *, name: str, company_id: str) -> Project:
        path = self._ep("projects_create")
        body = {"name": name, "companyId": company_id}
        payload = self._request_json("POST", path, json_body=body, ok_status=(200, 201))
        data = (payload or {}).get("data") or {}
        return self._map_project(data)

    def list_planned_tasks(
        self,
        *,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> List[Dict]:
        path = self._ep("planned_tasks_list")
        params: Dict[str, Any] = {"page": page, "limit": page_size}
        if project_id:
            params["projectId"] = project_id
        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        return (payload or {}).get("data", []) or []

    # ---------------- Time Entries ----------------
    def list_time_entries(
        self,
        *,
        employee_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        employee_status: str = "active",
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[TimeEntry], Dict]:
        path = self._ep("time_entries_list")
        params: Dict[str, Any] = {
            "page": page,
            "limit": page_size,
            "employeeStatus": employee_status,
        }
        if employee_id:
            params["employeeId"] = employee_id
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to

        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", []) or []
        meta = (payload or {}).get("meta", {}) or {}
        out = [self._map_time_entry(it) for it in data]
        return out, meta

    def start_time_entry(
        self,
        *,
        employee_id: str,
        project_id: str,
        tag_ids: List[str],
        comment: Optional[str] = None,
        coordinates: Optional[Dict] = None,
    ) -> Dict:
        path = self._ep("time_entries_start")
        body: Dict[str, Any] = {
            "employeeId": employee_id,
            "projectId": project_id,
            "tagIds": tag_ids,
        }
        if comment:
            body["comment"] = comment
        if coordinates:
            body["coordinates"] = coordinates

        payload = self._request_json("POST", path, json_body=body, ok_status=(200, 201))
        return payload

    def stop_time_entry(
        self,
        *,
        employee_id: str,
        comment: Optional[str] = None,
        coordinates: Optional[Dict] = None,
    ) -> Dict:
        # Si tu tenant no soporta /stop, ajusta endpoints.yaml o usa update_time_entry
        path = self._ep("time_entries_stop")
        body: Dict[str, Any] = {"employeeId": employee_id}
        if comment:
            body["comment"] = comment
        if coordinates:
            body["coordinates"] = coordinates
        payload = self._request_json("POST", path, json_body=body, ok_status=(200, 201))
        return payload

    def update_time_entry(self, *, time_entry_id: str, payload: Dict) -> Dict:
        tpl = self._ep("time_entries_update")
        path = tpl.format(id=time_entry_id)
        out = self._request_json("PUT", path, json_body=payload, ok_status=(200, 201))
        return out

    def delete_time_entry(self, *, time_entry_id: str) -> bool:
        tpl = self._ep("time_entries_delete")
        path = tpl.format(id=time_entry_id)
        _ = self._request_json("DELETE", path, ok_status=(200, 204))
        return True

    # ---------------- Work Entries ----------------
    def list_work_entries(
        self,
        *,
        employee_id: str,
        date_from: str,
        date_to: str,
        page: int = 1,
        page_size: int = 200,
        order_by: Optional[str] = None,
    ) -> List[WorkEntry]:
        path = self._ep("work_entries_list")
        params: Dict[str, Any] = {
            "employeeId": employee_id,
            "from": date_from,
            "to": date_to,
            "page": page,
            "limit": page_size,
        }
        if order_by:
            params["orderBy"] = order_by

        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", []) or []
        return [self._map_work_entry(it) for it in data]

    def create_work_entry(self, *, payload: Dict) -> WorkEntry:
        path = self._ep("work_entries_create")
        resp = self._request_json("POST", path, json_body=payload, ok_status=(200, 201))
        data = (resp or {}).get("data") or {}
        return self._map_work_entry(data)

    def update_work_entry(self, *, work_entry_id: str, payload: Dict) -> WorkEntry:
        tpl = self._ep("work_entries_update")
        path = tpl.format(id=work_entry_id)
        resp = self._request_json("PUT", path, json_body=payload, ok_status=(200, 201))
        data = (resp or {}).get("data") or {}
        return self._map_work_entry(data)

    def delete_work_entry(self, *, work_entry_id: str) -> bool:
        tpl = self._ep("work_entries_delete")
        path = tpl.format(id=work_entry_id)
        _ = self._request_json("DELETE", path, ok_status=(200, 204))
        return True

    def clock_in(self, *, payload: Dict) -> WorkEntry:
        path = self._ep("work_entries_clock_in")
        resp = self._request_json("POST", path, json_body=payload, ok_status=(200, 201))
        data = (resp or {}).get("data") or {}
        return self._map_work_entry(data)

    def clock_out(self, *, payload: Dict) -> WorkEntry:
        path = self._ep("work_entries_clock_out")
        resp = self._request_json("POST", path, json_body=payload, ok_status=(200, 201))
        data = (resp or {}).get("data") or {}
        return self._map_work_entry(data)

    # ---------------- Worked hours report ----------------
    def list_worked_hours_report(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        with_checks: bool = False,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[WorkedHoursStat], Dict]:
        path = self._ep("worked_hours_report_list")
        params: Dict[str, Any] = {
            "from": date_from,
            "to": date_to,
            "withChecks": str(with_checks).lower(),
            "page": page,
            "limit": page_size,
        }
        if employee_ids:
            # Swagger suele describir esto como employeeIds[in]
            params["employeeIds[in]"] = employee_ids

        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", []) or []
        meta = (payload or {}).get("meta", {}) or {}
        out = [self._map_worked_hours(it) for it in data]
        return out, meta

    # ---------------- Day offs ----------------
    def list_absence_day_off(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[AbsenceDayOff], Dict]:
        path = self._ep("absence_day_off_list")
        params: Dict[str, Any] = {"from": date_from, "to": date_to, "page": page, "limit": page_size}
        if order_by:
            params["orderBy"] = order_by
        if employee_ids:
            params["employeeIds[in]"] = employee_ids

        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", []) or []
        meta = (payload or {}).get("meta", {}) or {}
        out = [self._map_absence_day_off(it) for it in data]
        return out, meta

    def list_vacation_day_off(
        self,
        *,
        employee_ids: Optional[List[str]],
        date_from: str,
        date_to: str,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Tuple[List[VacationDayOff], Dict]:
        path = self._ep("vacation_day_off_list")
        params: Dict[str, Any] = {"from": date_from, "to": date_to, "page": page, "limit": page_size}
        if order_by:
            params["orderBy"] = order_by
        if employee_ids:
            params["employeeIds[in]"] = employee_ids

        payload = self._request_json("GET", path, params=params, ok_status=(200,))
        data = (payload or {}).get("data", []) or []
        meta = (payload or {}).get("meta", {}) or {}
        out = [self._map_vacation_day_off(it) for it in data]
        return out, meta

    # ---------------- Mappers ----------------
    @staticmethod
    def _map_employee(it: Dict[str, Any]) -> Employee:
        return Employee(
            id=str(it.get("id")),
            first_name=it.get("firstName"),
            last_name=it.get("lastName"),
            email=it.get("email"),
            status=it.get("status"),
            work_status=it.get("workStatus"),
            created_at=it.get("createdAt"),
            updated_at=it.get("updatedAt"),
            raw=it,
        )

    @staticmethod
    def _map_project(it: Dict[str, Any]) -> Project:
        # projectStatus puede venir como {"value":"active"} en algunos payloads
        status = it.get("projectStatus")
        if isinstance(status, dict):
            status = status.get("value")
        return Project(
            id=str(it.get("id")),
            name=it.get("name"),
            status=status,
            created_at=it.get("createdAt"),
            updated_at=it.get("updatedAt"),
            raw=it,
        )

    @staticmethod
    def _map_time_entry(it: Dict[str, Any]) -> TimeEntry:
        emp = it.get("employee") or {}
        prj = it.get("project") or None

        tags_block = it.get("tags") or {}
        tags_data = tags_block.get("data") if isinstance(tags_block, dict) else None
        tags: List[Tag] = []
        if isinstance(tags_data, list):
            for t in tags_data:
                if not isinstance(t, dict) or not t.get("id"):
                    continue
                tags.append(Tag(id=str(t.get("id")), name=t.get("name")))

        tin = it.get("timeEntryIn") or {}
        tout = it.get("timeEntryOut") or {}

        tin_coords = (tin.get("coordinates") or {}) if isinstance(tin, dict) else {}
        tout_coords = (tout.get("coordinates") or {}) if isinstance(tout, dict) else {}

        project_obj = None
        if isinstance(prj, dict) and prj.get("id"):
            project_obj = SesameRepository._map_project(prj)

        return TimeEntry(
            id=str(it.get("id")),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            project=project_obj,
            tags=tags,
            time_entry_in_at=tin.get("date") if isinstance(tin, dict) else None,
            time_entry_out_at=tout.get("date") if isinstance(tout, dict) else None,
            in_latitude=tin_coords.get("latitude"),
            in_longitude=tin_coords.get("longitude"),
            out_latitude=tout_coords.get("latitude"),
            out_longitude=tout_coords.get("longitude"),
            comment=it.get("comment"),
            created_at=it.get("createdAt"),
            updated_at=it.get("updatedAt"),
            deleted_at=it.get("deletedAt"),
            raw=it,
        )

    @staticmethod
    def _map_work_entry(it: Dict[str, Any]) -> WorkEntry:
        emp = it.get("employee") or {}
        pin = it.get("workEntryIn") or {}
        pout = it.get("workEntryOut") or {}

        pin_coords = (pin.get("coordinates") or {}) if isinstance(pin, dict) else {}
        pout_coords = (pout.get("coordinates") or {}) if isinstance(pout, dict) else {}

        return WorkEntry(
            id=str(it.get("id")),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            work_entry_type=it.get("workEntryType") or it.get("workEntry_type") or it.get("type"),
            work_check_type_id=it.get("workCheckTypeId") or it.get("workCheckType") or it.get("workCheckType_id"),
            in_at=pin.get("date") if isinstance(pin, dict) else None,
            out_at=pout.get("date") if isinstance(pout, dict) else None,
            in_latitude=pin_coords.get("latitude"),
            in_longitude=pin_coords.get("longitude"),
            out_latitude=pout_coords.get("latitude"),
            out_longitude=pout_coords.get("longitude"),
            in_office_id=pin.get("officeId") if isinstance(pin, dict) else None,
            out_office_id=pout.get("officeId") if isinstance(pout, dict) else None,
            worked_seconds=it.get("workedSeconds") or it.get("worked_seconds"),
            created_at=it.get("createdAt"),
            updated_at=it.get("updatedAt"),
            deleted_at=it.get("deletedAt"),
            raw=it,
        )

    @staticmethod
    def _map_worked_hours(it: Dict[str, Any]) -> WorkedHoursStat:
        return WorkedHoursStat(
            employee_id=str(it.get("employeeId") or it.get("employee_id")),
            seconds_worked=int(it.get("secondsWorked") or it.get("seconds_worked") or 0),
            seconds_to_work=it.get("secondsToWork"),
            seconds_balance=it.get("secondsBalance"),
        )

    @staticmethod
    def _map_absence_day_off(it: Dict[str, Any]) -> AbsenceDayOff:
        emp = it.get("employee") or {}
        abs_type = it.get("absenceType") or {}
        return AbsenceDayOff(
            id=str(it.get("id")),
            date=it.get("date"),
            seconds=it.get("seconds"),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            absence_type_id=abs_type.get("id"),
            absence_type_name=abs_type.get("name"),
            created_at=it.get("createdAt"),
            updated_at=it.get("updatedAt"),
            raw=it,
        )

    @staticmethod
    def _map_vacation_day_off(it: Dict[str, Any]) -> VacationDayOff:
        emp = it.get("employee") or {}
        vac_cfg = it.get("vacationConfiguration") or it.get("vacationConfig") or {}
        return VacationDayOff(
            id=str(it.get("id")),
            date=it.get("date"),
            seconds=it.get("seconds"),
            employee_id=emp.get("id"),
            employee_first_name=emp.get("firstName"),
            employee_last_name=emp.get("lastName"),
            employee_email=emp.get("email"),
            vacation_config_id=vac_cfg.get("id"),
            vacation_config_name=vac_cfg.get("name"),
            created_at=it.get("createdAt"),
            updated_at=it.get("updatedAt"),
            raw=it,
        )
