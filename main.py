# main.py
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Optional
from uuid import UUID

from sesame_connector.facades.sesame_client import SesameClient


Handler = Callable[[argparse.Namespace, SesameClient], int]


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def _json_default(o: Any) -> Any:
    """
    Encoder robusto para imprimir JSON en CLI/console.

    Motivo: algunas respuestas del cliente pueden contener datetime (u otros tipos)
    y json.dumps() estándar falla con:
      TypeError: Object of type datetime is not JSON serializable
    """
    # Fechas
    if isinstance(o, (datetime, date)):
        return o.isoformat()

    # Números exactos
    if isinstance(o, Decimal):
        # Si prefieres evitar pérdida de precisión, usa str(o)
        return float(o)

    # Identificadores / rutas
    if isinstance(o, (UUID, Path)):
        return str(o)

    # Enums
    if isinstance(o, Enum):
        return o.value

    # Colecciones
    if isinstance(o, (set, tuple)):
        return list(o)

    # Dataclasses
    if is_dataclass(o):
        return asdict(o)

    # Pydantic v2
    if hasattr(o, "model_dump") and callable(getattr(o, "model_dump")):
        return o.model_dump()

    # Pydantic v1
    if hasattr(o, "dict") and callable(getattr(o, "dict")):
        return o.dict()

    # Fallback (último recurso)
    return str(o)


def _print_json(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sesame-connector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ------------------------------------------------------------
    # employees-list
    # ------------------------------------------------------------
    p = sub.add_parser("employees-list", help="Listar empleados")
    p.add_argument("--only-active", action="store_true", default=False)
    p.add_argument("--page-size", type=int, default=200)
    p.set_defaults(handler=_cmd_employees_list)

    # ------------------------------------------------------------
    # projects-list
    # ------------------------------------------------------------
    p = sub.add_parser("projects-list", help="Listar proyectos")
    p.add_argument("--page-size", type=int, default=100)
    p.set_defaults(handler=_cmd_projects_list)

    # ------------------------------------------------------------
    # time-entries-list
    # ------------------------------------------------------------
    p = sub.add_parser("time-entries-list", help="Listar imputaciones (time entries)")
    p.add_argument("--employee-id", default=None)
    p.add_argument("--from", dest="date_from", default=None)
    p.add_argument("--to", dest="date_to", default=None)
    p.add_argument("--employee-status", default="active")
    p.add_argument("--page-size", type=int, default=50)
    p.add_argument("--all-pages", action="store_true", default=True)
    p.set_defaults(handler=_cmd_time_entries_list)

    # ------------------------------------------------------------
    # time-entries-start
    # ------------------------------------------------------------
    p = sub.add_parser("time-entries-start", help="Iniciar imputación a proyecto/tarea")
    p.add_argument("--employee-id", required=True)
    p.add_argument("--project-id", required=True)
    p.add_argument("--tag-id", required=False, default=None)
    p.add_argument("--comment", required=False, default="")
    p.set_defaults(handler=_cmd_time_entries_start)

    # ------------------------------------------------------------
    # time-entries-stop
    # ------------------------------------------------------------
    p = sub.add_parser("time-entries-stop", help="Parar imputación (cerrar time entry)")
    p.add_argument("--time-entry-id", required=True)
    p.add_argument("--comment", required=False, default=None)
    p.set_defaults(handler=_cmd_time_entries_stop)

    # ------------------------------------------------------------
    # work-entries-list
    # ------------------------------------------------------------
    p = sub.add_parser("work-entries-list", help="Listar fichajes (work entries)")
    p.add_argument("--employee-id", required=True)
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument("--page-size", type=int, default=200)
    p.add_argument("--all-pages", action="store_true", default=True)
    p.set_defaults(handler=_cmd_work_entries_list)

    # ------------------------------------------------------------
    # metrics-extract
    # ------------------------------------------------------------
    p = sub.add_parser("metrics-extract", help="Extraer métricas agregadas")
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument("--employee-id", action="append", dest="employee_ids", default=[])
    p.set_defaults(handler=_cmd_metrics_extract)

    return parser


# ---------------------------------------------------------------------
# Command handlers (usan SesameClient.execute)
# ---------------------------------------------------------------------
def _cmd_employees_list(args: argparse.Namespace, client: SesameClient) -> int:
    payload = {
        "only_active": bool(args.only_active) if args.only_active else None,
        "page_size": int(args.page_size),
    }
    res = client.execute("employees.list", payload)
    _print_json(res)
    return 0


def _cmd_projects_list(args: argparse.Namespace, client: SesameClient) -> int:
    # OJO: sólo funcionará si tu SesameClient soporta "projects.list".
    # Si tu implementación actual lo hace con otro action, cambia aquí la cadena.
    payload = {"page_size": int(args.page_size)}
    res = client.execute("projects.list", payload)
    _print_json(res)
    return 0


def _cmd_time_entries_list(args: argparse.Namespace, client: SesameClient) -> int:
    payload = {
        "employee_id": args.employee_id,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "employee_status": args.employee_status,
        "page_size": int(args.page_size),
        "all_pages": bool(args.all_pages),
    }
    res = client.execute("time_entries.list", payload)
    _print_json(res)
    return 0


def _cmd_time_entries_start(args: argparse.Namespace, client: SesameClient) -> int:
    # OJO: sólo funcionará si tu SesameClient soporta "time_entries.start"
    payload = {
        "employee_id": args.employee_id,
        "project_id": args.project_id,
        "tag_id": args.tag_id,
        "comment": args.comment,
    }
    res = client.execute("time_entries.start", payload)
    _print_json(res)
    return 0


def _cmd_time_entries_stop(args: argparse.Namespace, client: SesameClient) -> int:
    # OJO: sólo funcionará si tu SesameClient soporta "time_entries.stop"
    payload = {
        "time_entry_id": args.time_entry_id,
        "comment": args.comment,
    }
    res = client.execute("time_entries.stop", payload)
    _print_json(res)
    return 0


def _cmd_work_entries_list(args: argparse.Namespace, client: SesameClient) -> int:
    payload = {
        "employee_id": args.employee_id,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "page_size": int(args.page_size),
        "all_pages": bool(args.all_pages),
    }
    res = client.execute("work_entries.list", payload)
    _print_json(res)
    return 0


def _cmd_metrics_extract(args: argparse.Namespace, client: SesameClient) -> int:
    # OJO: depende de tu action real en SesameClient (ej: "metrics.extract")
    payload = {
        "date_from": args.date_from,
        "date_to": args.date_to,
        "employee_ids": args.employee_ids or None,
    }
    res = client.execute("metrics.extract", payload)
    _print_json(res)
    return 0


# ---------------------------------------------------------------------
# Entrypoint ejecutable desde código: main(argv)
# ---------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    _setup_logging()

    client = SesameClient.from_env()
    parser = build_parser()

    if argv is None:
        # Si algún día quieres volver a CLI real, podrías leer sys.argv aquí.
        # Pero tú has pedido NO usar consola, así que lo dejamos explícito.
        raise SystemExit("Este main requiere argv (lista de argumentos).")

    args = parser.parse_args(argv)

    handler: Handler = getattr(args, "handler", None)
    if handler is None:
        raise RuntimeError(f"Subcomando sin handler: {args.cmd!r}")

    return handler(args, client)


if __name__ == "__main__":
    # -----------------------------------------------------------------
    # Aquí defines “todos los comandos” que quieres ejecutar, en orden.
    # Cada comando es una lista como si fuera sys.argv[1:].
    # -----------------------------------------------------------------
    batch: List[List[str]] = [
        ["employees-list", "--only-active", "--page-size", "200"],
        ["projects-list", "--page-size", "100"],
        [
            "time-entries-list",
            "--employee-id",
            "9b58696a-d0d1-4294-b592-2f79a5436c77",
            "--from",
            "2025-12-01",
            "--to",
            "2026-01-01",
            "--employee-status",
            "active",
            "--page-size",
            "50",
        ],
        # Ejemplo start (si tu facade soporta action time_entries.start):
        # [
        #     "time-entries-start",
        #     "--employee-id", "9b58696a-d0d1-4294-b592-2f79a5436c77",
        #     "--project-id", "a4c075f3-d96e-4305-9637-5441e41a645c",
        #     "--tag-id", "52bcd468-2d15-4a05-8c95-410f7fd14b2d",
        #     "--comment", "Inicio vía código"
        # ],
    ]

    exit_code = 0
    for argv in batch:
        logging.getLogger(__name__).info("RUN CMD: %s", " ".join(argv))
        rc = main(argv)
        if rc != 0:
            exit_code = rc

    raise SystemExit(exit_code)
