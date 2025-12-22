# sesame_connector/config/endpoints_loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_ENDPOINTS_PATH = HERE / "endpoints.yaml"


def load_endpoints(path: str | Path | None = None) -> Dict[str, str]:
    """
    Carga endpoints desde YAML: clave -> ruta.
    """
    p = Path(path) if path is not None else DEFAULT_ENDPOINTS_PATH
    if not p.exists():
        raise FileNotFoundError(f"No se encontró el YAML de endpoints en: {p}")

    with p.open("r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("El YAML de endpoints debe ser un mapeo clave→ruta.")

    out: Dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(v, str):
            raise ValueError(f"Endpoint '{k}' debe ser string, recibido: {type(v).__name__}")
        v = v.strip()
        out[str(k)] = v if v.startswith("/") else f"/{v}"
    return out
