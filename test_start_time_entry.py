# test_start_time_entry.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

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
PROJECT_ID = os.getenv("PROJECT_ID", "a4c075f3-d96e-4305-9637-5441e41a645c").strip()
TAG_ID = os.getenv("TAG_ID", "52bcd468-2d15-4a05-8c95-410f7fd14b2d").strip()

COMMENT = os.getenv("COMMENT", "Inicio vía API: contando tiempo en api test tag").strip()


def headers() -> Dict[str, str]:
    return {
        "Authorization": f"{AUTH_SCHEME} {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not API_KEY:
        raise SystemExit("Falta SESAME_API_KEY en el .env")

    url = f"{BASE_URL}/project/v1/time-entries/start"
    body = {
        "employeeId": EMPLOYEE_ID,
        "projectId": PROJECT_ID,
        "tagIds": [TAG_ID],
        "comment": COMMENT,
        # "coordinates": {"latitude": 0, "longitude": 0},  # opcional
    }

    logging.info("POST %s", url)
    logging.info("Payload: %s", json.dumps(body, ensure_ascii=False))

    resp = requests.post(url, headers=headers(), json=body, timeout=TIMEOUT)
    logging.info("HTTP %s ctype=%s", resp.status_code, resp.headers.get("Content-Type", ""))

    try:
        payload: Any = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    print("\n==================== JSON RESPUESTA ====================\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("\n========================================================\n")

    if resp.status_code not in (200, 201):
        raise SystemExit(f"Error HTTP {resp.status_code}")


if __name__ == "__main__":
    main()
