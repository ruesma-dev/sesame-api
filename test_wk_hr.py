# test_time_entries_start.py  (reemplaza tu create_time_entry_in)
from __future__ import annotations
import json, logging, os, requests
from datetime import datetime
try:
    from dotenv import load_dotenv  # opcional
    load_dotenv()
except Exception:
    pass

BASE_URL = os.getenv("SESAME_BASE_URL", "https://api-eu4.sesametime.com").rstrip("/")
API_KEY = os.getenv("SESAME_API_KEY")
AUTH_SCHEME = os.getenv("SESAME_AUTH_SCHEME", "Bearer")
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
EMPLOYEE_ID = "9b58696a-d0d1-4294-b592-2f79a5436c77"
COMMENT = "Inicio sin proyecto via API (test)"
TZ_NAME = "Europe/Madrid"

def now_iso_in_tz(tz_name: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        return datetime.now(tz).isoformat(timespec="seconds")
    except Exception:
        return datetime.now().astimezone().isoformat(timespec="seconds")

def headers() -> dict[str, str]:
    return {
        "Authorization": f"{AUTH_SCHEME} {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def log_req(method: str, path: str, params: dict | None = None) -> None:
    req = requests.Request(method.upper(), f"{BASE_URL}{path}", params=params, headers=headers())
    prepped = req.prepare()
    logging.info("%s %s", method.upper(), prepped.url)

def create_time_entry_in(
    employee_id: str,
    comment: str,
    *,
    include_coordinates: bool = False,  # por defecto NO enviamos coordinates
) -> dict:
    path = "/project/v1/time-entries"
    time_entry_in: dict = {"date": now_iso_in_tz(TZ_NAME)}
    if include_coordinates:
        # Si quieres forzar envío, usa float reales
        time_entry_in["coordinates"] = {"latitude": 0.0, "longitude": 0.0}

    payload = {
        "employeeId": employee_id,
        "comment": comment,
        "timeEntryIn": time_entry_in,
        # IMPORTANTe: no enviar timeEntryOut para que quede abierto
    }

    log_req("POST", path)
    resp = requests.post(f"{BASE_URL}{path}", headers=headers(), json=payload, timeout=TIMEOUT)
    ctype = resp.headers.get("Content-Type", "")
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"create_time_entry_in: HTTP {resp.status_code} "
            f"ctype={ctype} body={resp.text[:800]!r}"
        )
    return resp.json()

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if not API_KEY:
        raise RuntimeError("Falta SESAME_API_KEY en el entorno (.env)")
    logging.info("Base: %s  Auth: %s  Timeout: %s", BASE_URL, AUTH_SCHEME, TIMEOUT)

    logging.info("== Iniciando time-entry (sin proyecto, solo timeEntryIn) ==")
    created = create_time_entry_in(EMPLOYEE_ID, COMMENT, include_coordinates=False)
    print(json.dumps(created, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
