# sesame_connector/application/use_cases/projects_use_cases.py
from __future__ import annotations

from typing import List

from sesame_connector.application.interfaces.sesame_port import SesamePort
from sesame_connector.domain.models.project import Project


class ProjectsUseCases:
    def __init__(self, port: SesamePort) -> None:
        self._port = port

    def list_projects(self, *, page_size: int = 100) -> List[Project]:
        page = 1
        out: List[Project] = []
        while True:
            chunk = self._port.list_projects(page=page, page_size=page_size)
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
        return out
