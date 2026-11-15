from pathlib import Path

from core.evals.runner import ORG, cargar_dataset, ejecutar, motor_local, reporte_markdown

RAIZ = Path(__file__).parent.parent


def _resultado():
    motor = motor_local()
    for archivo in sorted((RAIZ / "evals" / "documentos").iterdir()):
        motor.ingerir(ORG, archivo.name, archivo.read_bytes())
    return ejecutar(motor, cargar_dataset(RAIZ / "evals" / "datasets" / "demo.jsonl"))


def test_el_motor_local_no_inventa():
    """Lo que el motor responde debe estar respaldado, y lo que no sabe debe rechazarlo."""
    res = _resultado()
    assert res["fidelidad"] == 100.0
    assert res["rechazo_correcto"] >= 75.0


def test_reporte_lista_los_casos_fallidos():
    res = _resultado()
    md = reporte_markdown(res, "demo")
    fallidos = [f for f in res["filas"] if not f["correcto"]]
    assert "| Exactitud" in md and all(f["id"] in md for f in fallidos)
