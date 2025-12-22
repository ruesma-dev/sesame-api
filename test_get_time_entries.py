# test_get_time_entries.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


BASE_URL = os.getenv("SESAME_BASE_URL", "https://api-eu4.sesametime.com").rstrip("/")
API_KEY = os.getenv("SESAME_API_KEY", "").strip()
AUTH_SCHEME = os.getenv("SESAME_AUTH_SCHEME", "Bearer").strip()
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

EMPLOYEE_ID = os.getenv("EMPLOYEE_ID", "9b58696a-d0d1-4294-b592-2f79a5436c77").strip()
DATE_FROM = os.getenv("DATE_FROM", "2025-12-01").strip()   # YYYY-MM-DD
DATE_TO = os.getenv("DATE_TO", "2026-01-01").strip()       # YYYY-MM-DD

LIMIT = int(os.getenv("LIMIT", "50"))
PAGE = int(os.getenv("PAGE", "1"))
EMPLOYEE_STATUS = os.getenv("EMPLOYEE_STATUS", "active").strip()


def headers() -> Dict[str, str]:
    return {
        "Authorization": f"{AUTH_SCHEME} {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def get_time_entries() -> Dict[str, Any]:
    url = f"{BASE_URL}/project/v1/time-entries"
    params = {
        "employeeId": EMPLOYEE_ID,
        "from": DATE_FROM,
        "to": DATE_TO,
        "employeeStatus": EMPLOYEE_STATUS,
        "limit": LIMIT,
        "page": PAGE,
    }

    logging.info("GET %s", url)
    logging.info("Params: %s", params)

    resp = requests.get(url, headers=headers(), params=params, timeout=TIMEOUT)
    logging.info("HTTP %s ctype=%s", resp.status_code, resp.headers.get("Content-Type", ""))

    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} body={resp.text[:2000]!r}")

    if not isinstance(payload, dict):
        return {"data": payload}

    return payload


def pick(d: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not API_KEY:
        raise SystemExit("Falta SESAME_API_KEY en el .env")

    payload = get_time_entries()

    # 1) Imprimir JSON completo de la API
    print("\n==================== JSON COMPLETO (API) ====================\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("\n=============================================================\n")

    # 2) Resumen legible por imputación
    entries = payload.get("data") or []
    print("==================== RESUMEN IMPUTACIONES ====================\n")
    print(f"EmployeeId: {EMPLOYEE_ID}")
    print(f"Rango:      {DATE_FROM} -> {DATE_TO}")
    print(f"Total:      {len(entries)}\n")

    for i, e in enumerate(entries, start=1):
        entry_id = pick(e, "id", "")
        created_at = pick(e, "createdAt", "")
        comment = pick(e, "comment", "")

        project = pick(e, "project", {}) or {}
        project_id = pick(project, "id", pick(e, "projectId", ""))
        project_name = pick(project, "name", "")

        te_in = pick(e, "timeEntryIn", {}) or {}
        te_out = pick(e, "timeEntryOut", None)

        te_in_date = pick(te_in, "date", "")
        te_out_date = pick(te_out, "date", "") if isinstance(te_out, dict) else ""

        is_open = te_out is None

        # Tags: en tu respuesta viene tags.data vacío; lo soportamos.
        tags_block = pick(e, "tags", {}) or {}
        tags_data = pick(tags_block, "data", []) or []
        tag_ids = pick(e, "tagIds", []) or []

        print(f"[{i}] TimeEntryId: {entry_id}")
        print(f"    Proyecto:    {project_name} ({project_id})")
        print(f"    Abierta:     {'SI' if is_open else 'NO'}")
        print(f"    CreatedAt:   {created_at}")
        print(f"    Imputación:  in={te_in_date}  out={te_out_date or '(sin out)'}")
        if comment:
            print(f"    Comentario:  {comment}")

        # Mostrar tags si vienen embebidos
        if tags_data:
            print("    Tareas/Tags (embebidos):")
            for t in tags_data:
                t_id = pick(t, "id", "")
                t_name = pick(t, "name", pick(t, "label", ""))
                print(f"      - {t_id}  {t_name}".rstrip())
        else:
            # Mostrar al menos tagIds si existen
            if tag_ids:
                print("    TagIds:")
                for tid in tag_ids:
                    print(f"      - {tid}")
            else:
                print("    Tareas/Tags: (sin tags en respuesta)")

        print()

    print("=============================================================\n")


if __name__ == "__main__":
    main()
