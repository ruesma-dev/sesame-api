# sesame_connector/application/use_cases/employees_use_cases.py
from __future__ import annotations

from typing import List, Optional

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.employee import Employee


class EmployeeUseCases:
    def __init__(self, port: SesamePort) -> None:
        self._port = port

    def list_employees(self, *, only_active: Optional[bool] = None, page_size: int = 200) -> List[Employee]:
        page = 1
        out: List[Employee] = []
        while True:
            chunk = self._port.list_employees(only_active=only_active, page=page, page_size=page_size)
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
        return out
