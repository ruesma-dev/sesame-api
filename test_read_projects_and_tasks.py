# test_read_projects_and_tasks.py
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
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
PRINT_API_JSON = os.getenv("PRINT_API_JSON", "0").strip() == "1"


# Listado
PROJECT_NAME_FILTER = os.getenv("PROJECT_NAME", "").strip()
PROJECT_ID_FILTER = os.getenv("PROJECT_ID", "").strip()
PAGE_LIMIT = int(os.getenv("PAGE_LIMIT", "100"))
MAX_PROJECTS = int(os.getenv("MAX_PROJECTS", "20"))
SHOW_RAW = os.getenv("SHOW_RAW", "0").strip() == "1"

# Crear imputación al final
DO_CREATE_TIME_ENTRY = os.getenv("DO_CREATE_TIME_ENTRY", "1").strip() == "1"
TZ_NAME = os.getenv("TZ_NAME", "Europe/Madrid").strip()

EMPLOYEE_ID = os.getenv("EMPLOYEE_ID", "9b58696a-d0d1-4294-b592-2f79a5436c77").strip()
TARGET_PROJECT_ID = os.getenv("TARGET_PROJECT_ID", "a4c075f3-d96e-4305-9637-5441e41a645c").strip()

# OJO: esto era tu “tarea” (planned task) -> NO es tagId para time-entries
TARGET_PLANNED_TASK_ID = os.getenv(
    "TARGET_PLANNED_TASK_ID",
    "8882bb26-b734-41b6-b1fb-875b3bd61b3a",
).strip()

# Si conoces el tagId real, ponlo aquí y se saltará la resolución:
TARGET_TAG_ID = os.getenv("TARGET_TAG_ID", "").strip()

# Para resolver por nombre (recomendado ahora):
TARGET_TAG_NAME = os.getenv("TARGET_TAG_NAME", "API TEST PG").strip()


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"{AUTH_SCHEME} {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    ok_status: Tuple[int, ...] = (200,),
) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    logging.info("%s %s", method.upper(), url)

    resp = requests.request(
        method=method.upper(),
        url=url,
        headers=_headers(),
        params=params,
        json=json_body,
        timeout=TIMEOUT,
    )

    ctype = resp.headers.get("Content-Type", "")
    logging.info("HTTP %s ctype=%s", resp.status_code, ctype)

    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    if resp.status_code not in ok_status:
        preview = resp.text[:1200]
        raise RuntimeError(
            f"Sesame API error: {method.upper()} {path} -> HTTP {resp.status_code} body={preview!r}"
        )

    if not isinstance(payload, dict):
        return {"data": payload}

    return payload


def _try_request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Igual que antes, pero opcionalmente imprime el JSON de respuesta (incluye errores 4xx/5xx).
    Devuelve (status_code, payload_dict).
    """
    url = f"{BASE_URL}{path}"
    logging.info("%s %s", method.upper(), url)

    resp = requests.request(
        method=method.upper(),
        url=url,
        headers=_headers(),
        params=params,
        json=json_body,
        timeout=TIMEOUT,
    )

    ctype = resp.headers.get("Content-Type", "")
    logging.info("HTTP %s ctype=%s", resp.status_code, ctype)

    try:
        payload: Any = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    if not isinstance(payload, dict):
        payload = {"data": payload}

    if PRINT_API_JSON:
        print(f"\n--- API RESPONSE {method.upper()} {path} HTTP {resp.status_code} ---")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("--- END API RESPONSE ---\n")

    return resp.status_code, payload



def now_iso_tz(tz_name: str) -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz_name)).isoformat(timespec="seconds")
    except Exception:
        return datetime.now().astimezone().isoformat(timespec="seconds")


def list_projects(page: int, limit: int) -> List[Dict[str, Any]]:
    payload = _request(
        "GET",
        "/project/v1/projects",
        params={"page": page, "limit": limit},
        ok_status=(200,),
    )
    return payload.get("data") or []


def find_project_by_name(name: str) -> Optional[Dict[str, Any]]:
    target = name.strip().casefold()
    page = 1

    while True:
        chunk = list_projects(page=page, limit=PAGE_LIMIT)
        if not chunk:
            return None

        for prj in chunk:
            prj_name = (prj.get("name") or "").strip().casefold()
            if prj_name == target:
                return prj

        if len(chunk) < PAGE_LIMIT:
            return None

        page += 1


def list_planned_tasks(project_id: str, page: int, limit: int) -> List[Dict[str, Any]]:
    payload = _request(
        "GET",
        "/project/v1/planned-tasks",
        params={"projectId": project_id, "page": page, "limit": limit},
        ok_status=(200,),
    )
    return payload.get("data") or []


def fetch_all_planned_tasks(project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    page = 1

    while True:
        chunk = list_planned_tasks(project_id=project_id, page=page, limit=limit)
        if not chunk:
            break

        all_items.extend(chunk)

        if len(chunk) < limit:
            break

        page += 1

    return all_items


def fetch_tags_for_project(project_id: str) -> List[Dict[str, Any]]:
    """
    La documentación de Swagger está detrás de JS y según tenant puede variar.
    Probamos varios endpoints habituales para “tags/labels” hasta que alguno funcione.
    """
    candidates = [
        ("/project/v1/tags", {"projectId": project_id, "page": 1, "limit": PAGE_LIMIT}),
        ("/project/v1/project-tags", {"projectId": project_id, "page": 1, "limit": PAGE_LIMIT}),
        (f"/project/v1/projects/{project_id}/tags", {"page": 1, "limit": PAGE_LIMIT}),
        ("/project/v1/tags", None),  # algunos tenants listan todo sin filtro
    ]

    for path, params in candidates:
        status, payload = _try_request("GET", path, params=params)
        if status == 200:
            data = payload.get("data")
            if isinstance(data, list):
                return data
            # algunos endpoints devuelven data anidada
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data["data"]

    return []


def resolve_tag_id(project_id: str) -> str:
    """
    Regla:
      - si TARGET_TAG_ID viene informado => usarlo
      - si no, buscar tags del proyecto por nombre TARGET_TAG_NAME
      - si no, como fallback: si el id de planned-task coincide con algún tag id, usarlo
    """
    if TARGET_TAG_ID:
        return TARGET_TAG_ID

    tags = fetch_tags_for_project(project_id)
    if not tags:
        raise RuntimeError(
            "No he podido listar tags/etiquetas del proyecto (no encontré endpoint compatible). "
            "Pon SHOW_RAW=1 y pega un ejemplo de tag, o indica TARGET_TAG_ID directamente."
        )

    # 1) intentar por nombre
    if TARGET_TAG_NAME:
        target = TARGET_TAG_NAME.strip().casefold()
        for tag in tags:
            name = (tag.get("name") or tag.get("title") or tag.get("label") or "").strip()
            if name.casefold() == target:
                return str(tag.get("id") or "")

    # 2) fallback: ¿tu planned-task id es realmente un tag id?
    for tag in tags:
        if str(tag.get("id") or "") == TARGET_PLANNED_TASK_ID:
            return TARGET_PLANNED_TASK_ID

    # Si no, devolvemos diagnóstico
    sample = tags[0] if tags else {}
    raise RuntimeError(
        "No se pudo resolver tagId. "
        f"Probé por nombre TARGET_TAG_NAME={TARGET_TAG_NAME!r} y por id={TARGET_PLANNED_TASK_ID}. "
        f"Ejemplo de tag recibido: {json.dumps(sample, ensure_ascii=False)[:800]}"
    )


def create_time_entry_open(employee_id: str, project_id: str, tag_id: str, comment: str) -> Dict[str, Any]:
    body = {
        "employeeId": employee_id,
        "projectId": project_id,
        "tagIds": [tag_id],
        "comment": comment,
        "timeEntryIn": {"date": now_iso_tz(TZ_NAME)},
        # timeEntryOut fuera => “abierto / contando”
    }

    logging.info("POST %s/project/v1/time-entries", BASE_URL)
    logging.info("Payload time-entry: %s", json.dumps(body, ensure_ascii=False))

    status, payload = _try_request(
        "POST",
        "/project/v1/time-entries",
        json_body=body,
    )

    if status not in (200, 201):
        raise RuntimeError(
            f"POST /project/v1/time-entries -> HTTP {status} body={json.dumps(payload, ensure_ascii=False)[:1200]!r}"
        )

    return payload.get("data") or {}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not API_KEY:
        raise SystemExit("Falta SESAME_API_KEY en el entorno (.env).")

    logging.info("Base: %s  Auth: %s  Timeout: %ss", BASE_URL, AUTH_SCHEME, TIMEOUT)

    # 1) Resolver lista de proyectos a consultar
    projects: List[Dict[str, Any]] = []

    if PROJECT_ID_FILTER:
        logging.info("Filtrando por PROJECT_ID=%s (solo 1 proyecto)", PROJECT_ID_FILTER)
        page = 1
        found = None
        while True:
            chunk = list_projects(page=page, limit=PAGE_LIMIT)
            if not chunk:
                break
            for prj in chunk:
                if str(prj.get("id")) == PROJECT_ID_FILTER:
                    found = prj
                    break
            if found or len(chunk) < PAGE_LIMIT:
                break
            page += 1

        if not found:
            raise SystemExit(f"No se encontró el proyecto con id={PROJECT_ID_FILTER}")
        projects = [found]

    elif PROJECT_NAME_FILTER:
        logging.info("Filtrando por PROJECT_NAME=%r (solo 1 proyecto)", PROJECT_NAME_FILTER)
        found = find_project_by_name(PROJECT_NAME_FILTER)
        if not found:
            raise SystemExit(f"No se encontró el proyecto con nombre={PROJECT_NAME_FILTER!r}")
        projects = [found]

    else:
        logging.info("Sin filtros; listando hasta %s proyectos (MAX_PROJECTS)", MAX_PROJECTS)
        page = 1
        while len(projects) < MAX_PROJECTS:
            chunk = list_projects(page=page, limit=PAGE_LIMIT)
            if not chunk:
                break
            projects.extend(chunk)
            if len(chunk) < PAGE_LIMIT:
                break
            page += 1
        projects = projects[:MAX_PROJECTS]

    logging.info("Proyectos a consultar: %s", len(projects))
    print("\n==================== PROYECTOS Y TAREAS ====================\n")

    for idx, prj in enumerate(projects, start=1):
        prj_id = str(prj.get("id") or "")
        prj_name = (prj.get("name") or "").strip()

        print(f"[{idx}] Proyecto: {prj_name}  (id={prj_id})")

        if SHOW_RAW:
            print("  Proyecto RAW:")
            print(json.dumps(prj, ensure_ascii=False, indent=2))

        if not prj_id:
            print("  ⚠ Proyecto sin id; se omite.\n")
            continue

        tasks = fetch_all_planned_tasks(prj_id, limit=PAGE_LIMIT)

        print(f"  Planned tasks: {len(tasks)}")
        for t in tasks[:50]:
            t_id = str(t.get("id") or "")
            raw_name = (
                t.get("name")
                or t.get("title")
                or t.get("taskName")
                or t.get("label")
                or t.get("tag")
                or t.get("description")
            )
            if isinstance(raw_name, dict):
                raw_name = raw_name.get("name") or raw_name.get("label") or raw_name.get("title")

            t_name = str(raw_name or "").strip()
            print(f"   - {t_id}  {t_name or '(sin nombre en payload)'}")

        if SHOW_RAW and tasks:
            print("  Primera planned-task RAW:")
            print(json.dumps(tasks[0], ensure_ascii=False, indent=2))

        print()

    # 2) Crear time entry “abierto” para el empleado + proyecto + tag
    if DO_CREATE_TIME_ENTRY:
        if not EMPLOYEE_ID:
            raise SystemExit("Falta EMPLOYEE_ID en el entorno (.env).")
        if not TARGET_PROJECT_ID:
            raise SystemExit("Falta TARGET_PROJECT_ID en el entorno (.env).")
        if not TARGET_PLANNED_TASK_ID and not TARGET_TAG_ID and not TARGET_TAG_NAME:
            raise SystemExit("Falta TARGET_PLANNED_TASK_ID o TARGET_TAG_ID o TARGET_TAG_NAME en el entorno (.env).")

        print("\n==================== CREAR TIME ENTRY (ABIERTO) ====================\n")
        print(f"Empleado:         {EMPLOYEE_ID}")
        print(f"Proyecto:         {TARGET_PROJECT_ID}")
        print(f"PlannedTask (id): {TARGET_PLANNED_TASK_ID}")
        print(f"TagName:          {TARGET_TAG_NAME!r}")
        print()

        tag_id = resolve_tag_id(TARGET_PROJECT_ID)
        print(f"TagId resuelto para imputación: {tag_id}\n")

        created = create_time_entry_open(
            employee_id=EMPLOYEE_ID,
            project_id=TARGET_PROJECT_ID,
            tag_id=tag_id,
            comment=f"Inicio vía API: contando tiempo en tag '{TARGET_TAG_NAME}'",
        )

        print("Respuesta (data):")
        print(json.dumps(created, ensure_ascii=False, indent=2))
        print("\n====================================================================\n")

    print("============================================================\n")


if __name__ == "__main__":
    main()
