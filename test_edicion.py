# test_edicion_in_03012025.py
from __future__ import annotations
import json, logging, os, sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

def env_or_die(n: str) -> str:
    v = os.getenv(n)
    if not v:
        print(f"[FATAL] Falta {n}", file=sys.stderr); sys.exit(2)
    return v

BASE_URL = env_or_die("SESAME_BASE_URL").rstrip("/")
TOKEN = env_or_die("SESAME_API_KEY")
AUTH_SCHEME = os.getenv("SESAME_AUTH_SCHEME", "Bearer")
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Parámetros de la prueba
EMPLOYEE_ID = "9b58696a-d0d1-4294-b592-2f79a5436c77"
TARGET_DATE = "2025-10-07"   # viernes 3 de octubre de 2025
NEW_IN_TIME = (8, 39, 13)     # 08:25:03

# ─────────────────────────────────────────────────────────────
# LOG / HTTP
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("edit_in_first_entry")

session = requests.Session()
HEADERS = {
    "Authorization": f"{AUTH_SCHEME} {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

def prepared_url(method: str, path: str, params: Optional[Dict[str, Any]] = None) -> str:
    req = requests.Request(method=method.upper(), url=f"{BASE_URL}{path}", headers=HEADERS, params=params)
    return req.prepare().url  # type: ignore[return-value]

def http_get(path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    url = prepared_url("GET", path, params); log.info("HTTP GET %s", url)
    return session.get(url, headers=HEADERS, timeout=TIMEOUT)

def http_put(path: str, json_body: Dict[str, Any]) -> requests.Response:
    url = prepared_url("PUT", path, None); log.info("HTTP PUT %s", url)
    log.debug("PUT BODY: %s", json.dumps(json_body, ensure_ascii=False))
    return session.put(url, headers=HEADERS, json=json_body, timeout=TIMEOUT)

# ─────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────
def list_work_entries(employee_id: str, date_from: str, date_to: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Devuelve (entries_combinados, first_response_body).
    Imprimiremos first_response_body tal cual para ver el JSON crudo del primer GET.
    """
    path = "/schedule/v1/work-entries"
    page = 1
    combined: List[Dict[str, Any]] = []
    first_body: Dict[str, Any] = {}

    while True:
        params = {"page": page, "limit": 100, "employeeId": employee_id, "from": date_from, "to": date_to}
        resp = http_get(path, params)
        if not resp.ok:
            raise RuntimeError(f"list_work_entries: HTTP {resp.status_code} {resp.text[:240]!r}")
        body = resp.json()

        if page == 1:
            first_body = body

        items = body.get("data") or []
        combined.extend(items)

        meta = body.get("meta") or {}
        current = int(meta.get("currentPage", page))
        last = int(meta.get("lastPage", page))
        if current >= last or not items:
            break
        page += 1

    return combined, first_body

def update_work_entry(entry_id: str,
                      new_in_iso: str,
                      keep_out_iso: Optional[str],
                      keep_office_in: Optional[str],
                      keep_office_out: Optional[str],
                      work_entry_type: str) -> Dict[str, Any]:
    """
    Actualiza la ENTRADA (workEntryIn.date) a new_in_iso.
    Intenta marcar 'origin' como 'web' (si la API lo ignora, verás 'api' en la respuesta).
    Conserva la salida tal cual si existiese.
    """
    path = f"/schedule/v1/work-entries/{entry_id}"
    body: Dict[str, Any] = {
        "workEntryType": work_entry_type or "work",
        "workEntryIn": {
            "date": new_in_iso,
            "origin": "web",  # petición del usuario
        },
    }
    if keep_out_iso:
        body["workEntryOut"] = {"date": keep_out_iso, "origin": "web"}
    if keep_office_in:
        body.setdefault("workEntryIn", {})["officeId"] = keep_office_in
    if keep_office_out and "workEntryOut" in body:
        body.setdefault("workEntryOut", {})["officeId"] = keep_office_out

    resp = http_put(path, body)
    if not resp.ok:
        raise RuntimeError(f"update_work_entry: HTTP {resp.status_code} {resp.text[:300]!r}")
    return resp.json()

# ─────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────
def parse_iso(s: str) -> datetime:
    # Python 3.11+: datetime.fromisoformat soporta offset "+02:00"
    return datetime.fromisoformat(s)

def with_same_offset(date_str_ref: str, date_ymd: str, h: int, m: int, sec: int) -> str:
    """
    Construye un ISO con la misma zona/offset que date_str_ref, pero con Y-M-D de date_ymd y hora h:m:s.
    """
    ref = parse_iso(date_str_ref)
    y, mo, d = [int(x) for x in date_ymd.split("-")]
    dt_new = ref.replace(year=y, month=mo, day=d, hour=h, minute=m, second=sec, microsecond=0)
    return dt_new.isoformat()

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main() -> None:
    log.info("Base: %s  Auth: %s  Timeout: %s", BASE_URL, AUTH_SCHEME, TIMEOUT)

    # 1) GET de todos los fichajes del día (para el empleado)
    entries, first_body = list_work_entries(EMPLOYEE_ID, TARGET_DATE, TARGET_DATE)

    # 1.1) Muestra el JSON crudo del primer GET
    print("\n=== PRIMER GET (JSON crudo) ===")
    print(json.dumps(first_body, indent=2, ensure_ascii=False))

    if not entries:
        log.error("No hay fichajes para %s en %s", EMPLOYEE_ID, TARGET_DATE)
        sys.exit(1)

    # 2) Localizar la PRIMERA ENTRADA del día por workEntryIn.date (ascendente)
    def sort_key_first(e: Dict[str, Any]) -> datetime:
        s = ((e.get("workEntryIn") or {}).get("date"))
        try:
            return datetime.fromisoformat(s) if s else datetime.max
        except Exception:
            return datetime.max

    # Filtra solo aquellas con workEntryIn.date válido
    entries_with_in = [e for e in entries if (e.get("workEntryIn") or {}).get("date")]
    if not entries_with_in:
        log.error("No hay fichajes con workEntryIn en ese día")
        sys.exit(1)

    target = sorted(entries_with_in, key=sort_key_first, reverse=False)[0]

    entry_id = target.get("id")
    in_date = (target.get("workEntryIn") or {}).get("date")
    out_date = (target.get("workEntryOut") or {}).get("date")
    office_in = (target.get("workEntryIn") or {}).get("officeId")
    office_out = (target.get("workEntryOut") or {}).get("officeId")
    wtype = (target.get("workEntryType") or "").strip() or "work"

    # 3) Construir la nueva hora de ENTRADA con el mismo offset que la actual
    new_in_iso = with_same_offset(in_date, TARGET_DATE, *NEW_IN_TIME)

    log.info("Fichaje a editar (primera ENTRADA del día): id=%s", entry_id)
    log.info("Entrada actual: %s  →  Nueva entrada: %s", in_date, new_in_iso)
    if out_date:
        log.info("Salida actual se conserva: %s", out_date)
    log.info("Tipo actual: %s", wtype)

    # 4) PUT para fijar la nueva hora de ENTRADA (y mantener salida si existe)
    result = update_work_entry(entry_id, new_in_iso, out_date, office_in, office_out, wtype)

    # 5) Mostrar respuesta del PUT
    print("\n=== RESPUESTA PUT (JSON) ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.exception("Fallo en el test: %s", e); sys.exit(1)
