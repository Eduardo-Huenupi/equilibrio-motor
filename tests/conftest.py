from pathlib import Path

import pytest

from core.evals.runner import motor_local

DOCS = Path(__file__).parent.parent / "evals" / "documentos"


@pytest.fixture
def motor():
    """Motor local con los dos documentos de demostración cargados en la organización 'org-a'."""
    m = motor_local()
    for archivo in sorted(DOCS.iterdir()):
        m.ingerir("org-a", archivo.name, archivo.read_bytes(), "pruebas")
    return m
