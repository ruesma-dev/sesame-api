# config/endpoints_loader.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import yaml


def load_endpoints(path: str = "config/endpoints.yaml") -> Dict[str, str]:
    """
    Lee un YAML con pares clave→ruta y devuelve un dict[str, str].
    Lanza error claro si el archivo no existe o si el contenido no es válido.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No se encontró el YAML de endpoints en: {p}")
    with p.open("r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("El YAML de endpoints debe ser un mapeo clave→ruta.")
    # Normalizamos: quitar trailing slash y asegurar string
    out: Dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(v, str):
            raise ValueError(f"Endpoint '{k}' debe ser string, recibido: {type(v).__name__}")
        out[str(k)] = v if v.startswith("/") else f"/{v}"
    return out
