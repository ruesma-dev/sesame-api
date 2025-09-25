# interface_adapters/controllers/cli_controller.py
from __future__ import annotations

import calendar
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from application.use_cases.employee_use_cases import EmployeeUseCases
from application.use_cases.security_use_cases import SecurityUseCases
from application.use_cases.time_analytics_use_cases import (
    TimeAnalyticsUseCases,
)
from domain.models.work_entry import WorkEntry
from domain.models.hours_bag_history import HoursBagHistory
from infrastructure.filesystem.csv_repository import CsvRepository


class CLIController:
    """Controlador de demo (operaciones por pasos)."""

    def __init__(self, employee_uc: EmployeeUseCases, security_uc: SecurityUseCases) -> None:
        self._emp = employee_uc
        self._sec = security_uc
        self._logger = logging.getLogger(self.__class__.__name__)

    # ─────────────────────────────────────────────────────────────
    # Smoketest Token Info (RAW + parsed) → output/token_info_smoketest.json
    # ─────────────────────────────────────────────────────────────
    def run_token_smoketest(self) -> None:
        info = self._sec.show_token_info()
        self._logger.info("Parsed company: %s (%s)", info.company.name, info.company.id)

        # Acceso al repo para sacar RAW y metadatos de config
        from application.interfaces.sesame_port import SesamePort  # import diferido
        repo: SesamePort = self._emp._repo  # type: ignore[attr-defined]

        raw = repo.get_token_info_raw()  # cuerpo JSON tal cual
        # Intentamos sacar config (base_url, auth, token enmascarado)
        settings = getattr(getattr(self._emp, "_repo"), "_settings", None)  # type: ignore
        base_url = getattr(settings, "sesame_base_url", None)
        auth_scheme = getattr(settings, "sesame_auth_scheme", None)
        token = getattr(settings, "sesame_api_key", None)
        masked = None
        if token:
            masked = f"{token[:6]}...{token[-6:]}" if len(token) > 12 else "***"

        payload = {
            "base_url": base_url,
            "auth_scheme": auth_scheme,
            "token_masked": masked,
            "parsed_company": {
                "id": info.company.id,
                "name": info.company.name,
                "language": info.company.language,
                "notificationEmail": info.company.notification_email,
            },
            "raw_response": raw,
        }

        out = Path("output")
        out.mkdir(parents=True, exist_ok=True)
        target = out / "token_info_smoketest.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._logger.info("Token smoketest guardado en: %s", target)

    # ============== GET de todo el mes (work entries) ==============
    def run_get_work_entries_month(
        self,
        *,
        employee_id: str,
        year: int,
        month: int,
        suffix: Optional[str] = None,
    ) -> None:
        info = self._sec.show_token_info()
        self._logger.info("Company: %s (%s)", info.company.name, info.company.id)

        last_day = calendar.monthrange(year, month)[1]
        date_from = f"{year:04d}-{month:02d}-01"
        date_to = f"{year:04d}-{month:02d}-{last_day:02d}"
        self._logger.info(
            "GET Work Entries mes completo: %s → %s  employee_id=%s",
            date_from, date_to, employee_id
        )

        from application.interfaces.sesame_port import SesamePort
        repo: SesamePort = self._emp._repo  # type: ignore[attr-defined]

        entries: List[WorkEntry] = repo.list_work_entries(
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            page_size=1000,
        )
        self._logger.info("Total work entries en el mes: %s", len(entries))

        for w in entries[:5]:
            self._logger.info(" - id=%s  in=%s  out=%s  type=%s", w.id, w.in_at, w.out_at, w.work_entry_type)

        csv = CsvRepository(output_dir="output")
        path = csv.save_work_entries(entries)
        if suffix:
            self._logger.info("CSV (mes %s/%s, %s): %s", month, year, suffix, path)
        else:
            self._logger.info("CSV (mes %s/%s): %s", month, year, path)

    # ============== Reporte mensual compañía: horas por empleado/centro + coords ==============
    def run_company_hours_report_month(self, *, year: int, month: int) -> None:
        info = self._sec.show_token_info()
        self._logger.info("Company: %s (%s)", info.company.name, info.company.id)

        analytics = TimeAnalyticsUseCases(self._emp._repo)  # type: ignore[attr-defined]
        entries: List[WorkEntry] = analytics.get_company_work_entries_month(year=year, month=month)
        self._logger.info("Work entries mes %04d-%02d: %s", year, month, len(entries))

        by_emp = analytics.hours_by_employee(entries)
        rows_emp = [
            {
                "employee_id": e.employee_id,
                "employee_name": e.employee_name,
                "employee_email": e.employee_email,
                "total_seconds": e.total_seconds,
                "total_hours": round(e.total_seconds / 3600, 2),
            }
            for e in by_emp
        ]

        by_off = analytics.hours_by_office(entries)
        rows_off = [
            {
                "office_id": o.office_id,
                "total_seconds": o.total_seconds,
                "total_hours": round(o.total_seconds / 3600, 2),
            }
            for o in by_off
        ]

        rows_coords = analytics.coordinates_rows(entries)

        csv = CsvRepository(output_dir="output")
        path_emp = csv.save_hours_by_employee(rows_emp, year=year, month=month)
        path_off = csv.save_hours_by_office(rows_off, year=year, month=month)
        path_coords = csv.save_coordinates(rows_coords, year=year, month=month)

        self._logger.info("CSV horas por empleado: %s", path_emp)
        self._logger.info("CSV horas por centro:   %s", path_off)
        self._logger.info("CSV coordenadas:        %s", path_coords)

    # ============== Bolsa de horas: detalle + totales por empleado (mes) ==============
    def run_hours_bag_month(self, *, year: int, month: int, employee_ids: list[str] | None = None) -> None:
        info = self._sec.show_token_info()
        self._logger.info("Company: %s (%s)", info.company.name, info.company.id)

        analytics = TimeAnalyticsUseCases(self._emp._repo)  # type: ignore[attr-defined]
        items: List[HoursBagHistory] = analytics.get_hours_bag_month(
            year=year, month=month, employee_ids=employee_ids
        )
        self._logger.info("HoursBag movements %04d-%02d: %s", year, month, len(items))

        rows_detail = [
            {
                "id": it.id,
                "date": it.date,
                "employee_id": it.employee_id,
                "employee_name": it.employee_name,
                "hours_bag_rule_id": it.hours_bag_rule_id,
                "hours_bag_rule_name": it.hours_bag_rule_name,
                "hours_bag_rule_variation": it.hours_bag_rule_variation,
                "seconds": it.seconds,
                "check_seconds": it.check_seconds,
                "check_seconds_with_variation": it.check_seconds_with_variation,
            }
            for it in items
        ]

        from application.use_cases.time_analytics_use_cases import TimeAnalyticsUseCases as TA
        totals = TA.hours_bag_totals_by_employee(items)
        rows_totals = [
            {
                "employee_id": t.employee_id,
                "employee_name": t.employee_name,
                "seconds_sum": t.seconds_sum,
                "check_seconds_sum": t.check_seconds_sum,
                "check_seconds_with_variation_sum": t.check_seconds_with_variation_sum,
                "hours_sum": round(t.seconds_sum / 3600, 2),
                "check_hours_sum": round(t.check_seconds_sum / 3600, 2),
                "check_hours_with_variation_sum": round(t.check_seconds_with_variation_sum / 3600, 2),
            }
            for t in totals
        ]

        csv = CsvRepository(output_dir="output")
        path_detail = csv.save_hours_bag_history(rows_detail, year=year, month=month)
        path_totals = csv.save_hours_bag_totals_by_employee(rows_totals, year=year, month=month)
        self._logger.info("CSV bolsa de horas (detalle): %s", path_detail)
        self._logger.info("CSV bolsa de horas (totales por empleado): %s", path_totals)
