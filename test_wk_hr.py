# scripts/test_worked_hours_single.py
from __future__ import annotations

import json
import logging
from pathlib import Path

from config.settings import Settings
from config.endpoints_loader import load_endpoints
from infrastructure.http.http_client import HttpClient
from infrastructure.repositories.sesame_repository import SesameRepositoryImpl


def main() -> None:
    """
    Test muy sencillo para revisar el informe worked-hours de un empleado concreto
    en septiembre de 2025. Muestra por consola los segundos y las horas derivadas
    y guarda el payload crudo en output/test_worked_hours_2025-09_single.json
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("test_worked_hours_single")

    # ←— Parametriza aquí si quieres probar otro empleado/mes
    employee_id = "9b58696a-d0d1-4294-b592-2f79a5436c77"
    date_from = "2025-09-17"
    date_to = "2025-09-29"
    with_checks = False  # pon True si quieres que devuelva el array "checks"

    # Bootstrapping (reutilizamos tu infraestructura)
    settings = Settings.from_env()
    endpoints = load_endpoints(Path("config") / "endpoints.yaml")
    http = HttpClient.from_settings(settings)
    repo = SesameRepositoryImpl(settings, http, endpoints=endpoints)

    log.info(
        "Base=%s  Endpoint=%s  Emp=%s  Rango=%s→%s  withChecks=%s",
        settings.sesame_base_url,
        endpoints["worked_hours_report_list"],
        employee_id,
        date_from,
        date_to,
        with_checks,
    )

    # Llamada directa al repo (sin UC intermedio para simplificar el test)
    page = 1
    page_size = 100
    all_items = []
    last_page_seen = None

    while True:
        items, meta = repo.list_worked_hours_report(
            employee_ids=[employee_id],
            date_from=date_from,
            date_to=date_to,
            with_checks=with_checks,
            page=page,
            page_size=page_size,
        )
        all_items.extend(items)

        current = int(meta.get("currentPage") or page)
        last_page = int(meta.get("lastPage") or current)
        last_page_seen = last_page
        logging.info("Página %d de %d, registros página=%d, acumulados=%d",
                     current, last_page, len(items), len(all_items))
        if current >= last_page or not items:
            break
        page += 1

    # Guardamos crudo para inspección
    out_json = Path("output") / "test_worked_hours_2025-09_single.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "employeeId": employee_id,
                "from": date_from,
                "to": date_to,
                "pages": last_page_seen or 1,
                "items": [i.model_dump(mode="python") for i in all_items],
            },
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    # Impresión “audit-friendly” en consola
    if not all_items:
        log.warning("La API devolvió 0 items para ese empleado y rango.")
        print("\nRESULTADO: 0 registros")
        print(f"JSON crudo: {out_json}")
        return

    # El endpoint devuelve 1 fila por empleado en el rango (normalmente)
    s = all_items[0]
    sw = int(s.seconds_worked or 0)
    stw = int(s.seconds_to_work or 0) if s.seconds_to_work is not None else None
    sba = int(s.seconds_balance) if s.seconds_balance is not None else (sw - (stw or 0))

    print("\n===== Worked Hours (Sesame) – TEST ÚNICO =====")
    print(f"Empleado:            {employee_id}")
    print(f"Rango:               {date_from} → {date_to}")
    print(f"secondsWorked:       {sw}  ({round(sw/3600.0, 2)} h)")
    print(f"secondsToWork:       {stw if stw is not None else '-'}  "
          f"({round(stw/3600.0, 2) if stw is not None else '-'} h)")
    print(f"secondsBalance:      {s.seconds_balance if s.seconds_balance is not None else '-'}  "
          f"({round(sba/3600.0, 2) if s.seconds_balance is not None else '-'} h)")
    if s.checks is not None:
        print(f"checks:              {len(s.checks)} elementos (withChecks={with_checks})")
    print(f"JSON crudo guardado: {out_json}")


if __name__ == "__main__":
    main()
