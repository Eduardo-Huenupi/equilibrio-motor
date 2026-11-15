"""Demo local: carga los documentos de ejemplo y levanta la API con claves de demostración.

Solo para mostrar el producto en tu computador. Las claves 'demo-*' no deben usarse en producción.
"""
from __future__ import annotations

from pathlib import Path

import uvicorn

from apps.api.main import Identidad, crear_app
from core.evals.runner import motor_local

DOCS = Path(__file__).parent.parent.parent / "evals" / "documentos"
CLAVES = {
    "demo-admin": Identidad("org-demo", "admin", "admin"),
    "demo-lector": Identidad("org-demo", "lector", "lector"),
}


def main() -> None:
    motor = motor_local()
    for archivo in sorted(DOCS.iterdir()):
        motor.ingerir("org-demo", archivo.name, archivo.read_bytes(), "demo")
    print("Demo en http://localhost:8000 · clave: demo-admin")
    uvicorn.run(crear_app(motor=motor, claves=CLAVES), host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
