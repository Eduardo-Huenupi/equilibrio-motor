"""Evals: convierten "funciona bien" en números y frenan los cambios que empeoran el motor.

Uso:
    python -m core.evals.runner --dataset evals/datasets/demo.jsonl --docs evals/documentos

Formato del dataset (una línea JSON por caso):
    {"id": "...", "pregunta": "...", "tipo": "normal|dificil|sin_respuesta",
     "documento": "archivo.txt", "pagina": 2, "esperado": ["texto que debe aparecer"]}
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.governance.auditoria import RegistroAuditoria
from core.modelos import Respuesta
from core.motor import Motor
from core.rag.almacen import AlmacenMemoria
from core.rag.embeddings import EmbedderHash
from core.rag.llm import LLMExtractivo
from core.texto import normalizar, tokens

ORG = "org-evals"


def cargar_dataset(ruta: Path) -> list[dict]:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def _fiel(r: Respuesta) -> bool:
    """Fidelidad: al menos el 80% de las palabras de la respuesta están en los fragmentos citados."""
    palabras = set(tokens(r.texto))
    if not palabras:
        return False
    respaldo = set()
    for c in r.citas:
        respaldo |= set(tokens(r.recuperados[c.n - 1].fragmento.texto))
    return len(palabras & respaldo) / len(palabras) >= 0.8


def evaluar_caso(motor: Motor, caso: dict) -> dict:
    r = motor.preguntar(ORG, caso["pregunta"], "evals")
    fila = {
        "id": caso["id"], "tipo": caso["tipo"], "pregunta": caso["pregunta"],
        "respuesta": r.texto, "rechazada": r.rechazada, "latencia_ms": r.latencia_ms,
    }
    if caso["tipo"] == "sin_respuesta":
        fila["correcto"] = r.rechazada
        return fila
    fila["recuperado"] = any(
        x.fragmento.documento_nombre == caso["documento"] and x.fragmento.pagina == caso["pagina"]
        for x in r.recuperados
    )
    texto = normalizar(r.texto)
    fila["correcto"] = not r.rechazada and all(normalizar(e) in texto for e in caso["esperado"])
    fila["cita_correcta"] = any(
        c.documento == caso["documento"] and c.pagina == caso["pagina"] for c in r.citas
    )
    fila["fiel"] = (not r.rechazada) and _fiel(r)
    return fila


def _pct(valores: list[bool]) -> float:
    return round(100 * sum(valores) / len(valores), 1) if valores else 0.0


def ejecutar(motor: Motor, dataset: list[dict]) -> dict:
    filas = [evaluar_caso(motor, caso) for caso in dataset]
    con = [f for f in filas if f["tipo"] != "sin_respuesta"]
    sin = [f for f in filas if f["tipo"] == "sin_respuesta"]
    respondidas = [f for f in con if not f["rechazada"]]
    latencias = sorted(f["latencia_ms"] for f in filas)
    return {
        "casos": len(filas),
        "exactitud": _pct([f["correcto"] for f in con]),
        "recuperacion": _pct([f["recuperado"] for f in con]),
        "cita_correcta": _pct([f["cita_correcta"] for f in con]),
        "fidelidad": _pct([f["fiel"] for f in respondidas]),
        "rechazo_correcto": _pct([f["correcto"] for f in sin]),
        "latencia_p50_ms": round(statistics.median(latencias), 1) if latencias else 0.0,
        "latencia_p95_ms": round(latencias[int(0.95 * (len(latencias) - 1))], 1) if latencias else 0.0,
        "filas": filas,
    }


def reporte_markdown(res: dict, titulo: str) -> str:
    lineas = [
        f"# Reporte de evals: {titulo}",
        "",
        f"Fecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Casos: {res['casos']}",
        "",
        "| Métrica | Resultado |",
        "| --- | --- |",
        f"| Exactitud (preguntas con respuesta) | {res['exactitud']}% |",
        f"| Recuperación (página correcta entre los fragmentos) | {res['recuperacion']}% |",
        f"| Cita correcta (documento y página) | {res['cita_correcta']}% |",
        f"| Fidelidad (respuesta respaldada por lo citado) | {res['fidelidad']}% |",
        f"| Rechazo correcto (preguntas sin respuesta) | {res['rechazo_correcto']}% |",
        f"| Latencia p50 / p95 | {res['latencia_p50_ms']} / {res['latencia_p95_ms']} ms |",
        "",
        "## Casos fallidos",
        "",
    ]
    fallidos = [f for f in res["filas"] if not f["correcto"]]
    if not fallidos:
        lineas.append("Ninguno.")
    for f in fallidos:
        lineas.append(f"- **{f['id']}** ({f['tipo']}): {f['pregunta']} → {f['respuesta']}")
    return "\n".join(lineas) + "\n"


def motor_local() -> Motor:
    """Motor sin claves ni red: resultados reproducibles para CI."""
    return Motor(AlmacenMemoria(), EmbedderHash(), LLMExtractivo(), RegistroAuditoria())


def main() -> int:
    p = argparse.ArgumentParser(description="Corre los evals del motor.")
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--docs", type=Path, required=True)
    p.add_argument("--reporte", type=Path, default=Path("evals/reportes/ultimo.md"))
    p.add_argument("--min-exactitud", type=float, default=0.0)
    p.add_argument("--min-fidelidad", type=float, default=0.0)
    p.add_argument("--min-rechazo", type=float, default=0.0)
    a = p.parse_args()

    motor = motor_local()
    for archivo in sorted(a.docs.iterdir()):
        if archivo.is_file():
            motor.ingerir(ORG, archivo.name, archivo.read_bytes(), "evals")
    res = ejecutar(motor, cargar_dataset(a.dataset))
    a.reporte.parent.mkdir(parents=True, exist_ok=True)
    a.reporte.write_text(reporte_markdown(res, a.dataset.stem), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "filas"}, ensure_ascii=False, indent=2))

    fallas = [
        f"{nombre} {res[clave]}% < mínimo {minimo}%"
        for nombre, clave, minimo in (
            ("exactitud", "exactitud", a.min_exactitud),
            ("fidelidad", "fidelidad", a.min_fidelidad),
            ("rechazo correcto", "rechazo_correcto", a.min_rechazo),
        )
        if res[clave] < minimo
    ]
    for f in fallas:
        print("FALLA:", f, file=sys.stderr)
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
