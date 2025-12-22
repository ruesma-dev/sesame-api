# test_time_entries.py
from __future__ import annotations
import os, json, logging, requests
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
BASE_URL    = os.getenv("SESAME_BASE_URL", "https://api-eu4.sesametime.com").rstrip("/")
API_KEY     = os.getenv("SESAME_API_KEY")
AUTH_SCHEME = os.getenv("SESAME_AUTH_SCHEME", "Bearer")
TIMEOUT     = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

EMPLOYEE_ID  = "9b58696a-d0d1-4294-b592-2f79a5436c77"
PROJECT_ID   = os.getenv("PROJECT_ID", "").strip()
PROJECT_NAME = os.getenv("PROJECT_NAME", "API Test Project").strip()
COMPANY_ID   = os.getenv("COMPANY_ID", "").strip()   # opcional; si no está, lo leeremos de /core/v3/info
TZ_NAME      = os.getenv("TZ_NAME", "Europe/Madrid")

# ─────────────────────────────────────────────────────────────
# Helpers HTTP
# ─────────────────────────────────────────────────────────────
def headers() -> dict[str, str]:
    return {
        "Authorization": f"{AUTH_SCHEME} {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def prepared_url(method: str, path: str, params: dict | None = None) -> str:
    req = requests.Request(method.upper(), f"{BASE_URL}{path}", params=params, headers=headers())
    return req.prepare().url  # type: ignore[return-value]

def now_iso_tz(tz_name: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name)).isoformat(timespec="seconds")
    except Exception:
        return datetime.now().astimezone().isoformat(timespec="seconds")

# ─────────────────────────────────────────────────────────────
# Core: company info
# ─────────────────────────────────────────────────────────────
def get_company_info() -> dict:
    path = "/core/v3/info"
    url = prepared_url("GET", path)
    logging.info("GET %s", url)
    resp = requests.get(url, headers=headers(), timeout=TIMEOUT)
    try:
        parsed = resp.json()
    except Exception:
        parsed = None
    if resp.status_code != 200:
        raise RuntimeError(f"token_info: HTTP {resp.status_code} body={resp.text[:800]!r}")
    return (parsed or {}).get("data", {}).get("company", {})  # {"id","name",...}

def resolve_company_id() -> str:
    if COMPANY_ID:
        logging.info("Usando COMPANY_ID de entorno: %s", COMPANY_ID)
        return COMPANY_ID
    logging.info("COMPANY_ID no definido; obtenemos de /core/v3/info")
    c = get_company_info()
    cid = c.get("id")
    if not cid:
        raise SystemExit("No se pudo resolver companyId desde /core/v3/info.")
    logging.info("Company: %s (%s)", c.get("name"), cid)
    return cid

# ─────────────────────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────────────────────
def list_projects(page: int = 1, limit: int = 100) -> list[dict]:
    path = "/project/v1/projects"
    params = {"page": page, "limit": limit}
    url = prepared_url("GET", path, params=params)
    logging.info("GET %s", url)
    resp = requests.get(url, headers=headers(), timeout=TIMEOUT)
    try:
        data = resp.json()
    except Exception:
        data = None
    if resp.status_code != 200:
        raise RuntimeError(f"list_projects: HTTP {resp.status_code} body={resp.text[:800]!r}")
    return (data or {}).get("data", [])

def find_project_by_name(name: str) -> dict | None:
    page = 1
    while True:
        chunk = list_projects(page=page, limit=100)
        if not chunk:
            return None
        for prj in chunk:
            if (prj.get("name") or "").strip().lower() == name.strip().lower():
                return prj
        if len(chunk) < 100:
            return None
        page += 1

def create_project(name: str, company_id: str) -> dict:
    path = "/project/v1/projects"
    # Payload mínimo + campos habituales; ajusta si tu API exige otros
    body = {
        "name": name,
        "companyId": company_id,
        # Si tu tenant exige más:
        # "status": "open",
        # "description": "Proyecto creado desde script de pruebas",
        # "startDate": now_iso_tz(TZ_NAME)[:10],
    }
    url = prepared_url("POST", path)
    logging.info("POST %s", url)
    logging.info("Payload (create project): %s", json.dumps(body, ensure_ascii=False))
    resp = requests.post(url, headers=headers(), json=body, timeout=TIMEOUT)
    ctype = resp.headers.get("Content-Type", "")
    logging.info("HTTP %s ctype=%s", resp.status_code, ctype)
    try:
        parsed = resp.json()
    except Exception:
        parsed = None
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"create_project: HTTP {resp.status_code} body={resp.text[:800]!r}")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return (parsed or {}).get("data") or {}

# ─────────────────────────────────────────────────────────────
# Time Entries
# ─────────────────────────────────────────────────────────────
def create_time_entry(employee_id: str, project_id: str, comment: str) -> dict:
    path = "/project/v1/time-entries"
    body = {
        "employeeId": employee_id,
        "projectId": project_id,
        "comment": comment,
        "timeEntryIn": {
            "date": now_iso_tz(TZ_NAME)
            # "coordinates": {"latitude": 40.0, "longitude": -3.7}  # solo si lo necesitas
        }
    }
    url = prepared_url("POST", path)
    logging.info("POST %s", url)
    logging.info("Payload (time-entry): %s", json.dumps(body, ensure_ascii=False))
    resp = requests.post(url, headers=headers(), json=body, timeout=TIMEOUT)
    ctype = resp.headers.get("Content-Type", "")
    logging.info("HTTP %s ctype=%s", resp.status_code, ctype)
    try:
        parsed = resp.json()
    except Exception:
        parsed = None
    if parsed is not None:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print(resp.text)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"create_time_entry: HTTP {resp.status_code} body={resp.text[:800]!r}")
    return (parsed or {}).get("data") or {}

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if not API_KEY:
        raise SystemExit("Falta SESAME_API_KEY en el entorno (.env).")
    logging.info("Base: %s  Auth: %s  Timeout: %s", BASE_URL, AUTH_SCHEME, TIMEOUT)

    # 1) Resolver companyId (para crear proyecto si hiciera falta)
    company_id = resolve_company_id()

    # 2) Resolver projectId
    project_id = PROJECT_ID
    used_name = None
    if project_id:
        logging.info("Usando PROJECT_ID de entorno: %s", project_id)
    else:
        logging.info("PROJECT_ID no definido; buscamos proyecto por nombre: %r", PROJECT_NAME)
        prj = find_project_by_name(PROJECT_NAME)
        if prj:
            project_id = prj.get("id")
            used_name = prj.get("name")
            logging.info("Proyecto encontrado: %s (%s)", used_name, project_id)
        else:
            logging.info("No existe proyecto %r; intentamos crearlo…", PROJECT_NAME)
            prj = create_project(PROJECT_NAME, company_id)
            project_id = prj.get("id")
            used_name = prj.get("name")
            logging.info("Proyecto creado: %s (%s)", used_name, project_id)

    if not project_id:
        raise SystemExit("No se ha podido resolver projectId. Revisa permisos/campos requeridos o define PROJECT_ID en .env.")

    # 3) Crear time entry (solo entrada)
    comment = f"Inicio vía script (proyecto={used_name or project_id})"
    _ = create_time_entry(EMPLOYEE_ID, project_id, comment)

if __name__ == "__main__":
    main()
