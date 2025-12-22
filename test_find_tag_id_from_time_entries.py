# test_find_tag_id_from_time_entries.py
from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

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
PROJECT_ID = os.getenv("TARGET_PROJECT_ID", "a4c075f3-d96e-4305-9637-5441e41a645c").strip()
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "30"))

def headers() -> Dict[str, str]:
    return {
        "Authorization": f"{AUTH_SCHEME} {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def req(method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    logging.info("%s %s", method.upper(), url)
    r = requests.request(method.upper(), url, headers=headers(), params=params, timeout=TIMEOUT)
    logging.info("HTTP %s ctype=%s", r.status_code, r.headers.get("Content-Type", ""))
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text}
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} body={r.text[:1200]!r}")
    return payload if isinstance(payload, dict) else {"data": payload}

def list_time_entries(employee_id: str, from_d: date, to_d: date, page: int, limit: int = 100) -> List[Dict[str, Any]]:
    params = {
        "employeeId": employee_id,
        "from": from_d.isoformat(),
        "to": to_d.isoformat(),
        "page": page,
        "limit": limit,
        "employeeStatus": "active",
    }
    payload = req("GET", "/project/v1/time-entries", params=params)
    return payload.get("data") or []

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if not API_KEY:
        raise SystemExit("Falta SESAME_API_KEY en .env")

    to_d = date.today()
    from_d = to_d - timedelta(days=LOOKBACK_DAYS)

    all_entries: List[Dict[str, Any]] = []
    page = 1
    while True:
        chunk = list_time_entries(EMPLOYEE_ID, from_d, to_d, page=page, limit=100)
        if not chunk:
            break
        all_entries.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1

    # Filtrar por proyecto
    proj_entries = [e for e in all_entries if str(e.get("projectId") or "") == PROJECT_ID]

    print("\n==================== TIME ENTRIES (FILTRADO) ====================\n")
    print(f"Empleado: {EMPLOYEE_ID}")
    print(f"Proyecto: {PROJECT_ID}")
    print(f"Rango:    {from_d} -> {to_d}")
    print(f"Entradas: {len(proj_entries)}\n")

    # Mostrar los tagIds encontrados
    tag_counts: Dict[str, int] = {}
    for e in proj_entries:
        for tid in (e.get("tagIds") or []):
            tid_s = str(tid)
            tag_counts[tid_s] = tag_counts.get(tid_s, 0) + 1

    if not tag_counts:
        print("No hay tagIds en las entradas encontradas. Crea una imputación en la UI y reintenta.")
        return

    print("TagIds detectados (con conteo):")
    for tid, cnt in sorted(tag_counts.items(), key=lambda kv: kv[1], reverse=True):
        print(f" - {tid}  (count={cnt})")

    # Mostrar 3 entradas de ejemplo para inspección
    print("\nEjemplos (hasta 3):")
    for e in proj_entries[:3]:
        print(json.dumps(
            {
                "id": e.get("id"),
                "projectId": e.get("projectId"),
                "tagIds": e.get("tagIds"),
                "timeEntryIn": (e.get("timeEntryIn") or {}).get("date"),
                "timeEntryOut": (e.get("timeEntryOut") or {}).get("date"),
                "comment": e.get("comment"),
            },
            ensure_ascii=False,
            indent=2
        ))

    print("\n=================================================================\n")

if __name__ == "__main__":
    main()
