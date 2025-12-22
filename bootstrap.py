# sesame_connector/bootstrap.py
from __future__ import annotations

from dataclasses import dataclass

from sesame_connector.application.use_cases.day_off_use_cases import DayOffUseCases
from sesame_connector.application.use_cases.employee_metrics_use_cases import EmployeeMetricsUseCases
from sesame_connector.application.use_cases.employee_use_cases import EmployeeUseCases
from sesame_connector.application.use_cases.projects_use_cases import ProjectsUseCases
from sesame_connector.application.use_cases.time_entries_use_cases import TimeEntriesUseCases
from sesame_connector.application.use_cases.work_entries_use_cases import WorkEntriesUseCases
from sesame_connector.application.use_cases.worked_hours_use_cases import WorkedHoursUseCases
from sesame_connector.config.endpoints_loader import load_endpoints
from sesame_connector.config.settings import Settings
from sesame_connector.infrastructure.http.http_client import HttpClient
from sesame_connector.infrastructure.repositories.sesame_repository import SesameRepository


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    repo: SesameRepository

    employees_uc: EmployeeUseCases
    projects_uc: ProjectsUseCases
    work_entries_uc: WorkEntriesUseCases
    time_entries_uc: TimeEntriesUseCases
    worked_hours_uc: WorkedHoursUseCases
    day_off_uc: DayOffUseCases
    employee_metrics_uc: EmployeeMetricsUseCases


def build_container() -> Container:
    settings = Settings.from_env()
    endpoints = load_endpoints()
    http = HttpClient.from_settings(settings)
    repo = SesameRepository(http=http, endpoints=endpoints)

    employees_uc = EmployeeUseCases(repo)
    projects_uc = ProjectsUseCases(repo)
    work_entries_uc = WorkEntriesUseCases(repo)
    time_entries_uc = TimeEntriesUseCases(repo)
    worked_hours_uc = WorkedHoursUseCases(repo)
    day_off_uc = DayOffUseCases(repo)
    metrics_uc = EmployeeMetricsUseCases(
        employee_uc=employees_uc,  # <- antes: employees_uc=employees_uc
        worked_hours_uc=worked_hours_uc,
        day_off_uc=day_off_uc,
        time_entries_uc=time_entries_uc,
    )
    return Container(
        settings=settings,
        repo=repo,
        employees_uc=employees_uc,
        projects_uc=projects_uc,
        work_entries_uc=work_entries_uc,
        time_entries_uc=time_entries_uc,
        worked_hours_uc=worked_hours_uc,
        day_off_uc=day_off_uc,
        employee_metrics_uc=metrics_uc,
    )
