"""Arma la respuesta final: o viene con citas verificables, o se rechaza."""
from __future__ import annotations

import re

from core.modelos import Cita, Respuesta, Resultado

from .llm import LLM, NO_ENCONTRADO

SIN_RESPALDO = "No encontré esa información en los documentos disponibles."


def responder(llm: LLM, pregunta: str, resultados: list[Resultado], umbral: float) -> Respuesta:
    """Tres barreras contra respuestas inventadas:

    1. Si nada de lo recuperado se parece lo suficiente a la pregunta, ni se llama al modelo.
    2. Si el modelo dice NO_ENCONTRADO, se rechaza.
    3. Si el modelo responde sin citar un fragmento real, se rechaza.
    """
    if not resultados or max(r.similitud for r in resultados) < umbral:
        return Respuesta(SIN_RESPALDO, rechazada=True, motivo="sin_evidencia", recuperados=resultados)

    gen = llm.generar(pregunta, [r.fragmento.texto for r in resultados])
    base = dict(
        tokens_entrada=gen.tokens_entrada, tokens_salida=gen.tokens_salida, recuperados=resultados
    )
    if NO_ENCONTRADO in gen.texto:
        return Respuesta(SIN_RESPALDO, rechazada=True, motivo="modelo_sin_respaldo", **base)

    numeros = sorted({int(n) for n in re.findall(r"\[(\d+)\]", gen.texto)})
    validos = [n for n in numeros if 1 <= n <= len(resultados)]
    if not validos or len(validos) != len(numeros):
        return Respuesta(SIN_RESPALDO, rechazada=True, motivo="sin_citas_validas", **base)

    citas = [
        Cita(
            n,
            resultados[n - 1].fragmento.documento_nombre,
            resultados[n - 1].fragmento.pagina,
            resultados[n - 1].fragmento.texto[:300],
        )
        for n in validos
    ]
    return Respuesta(gen.texto, citas=citas, **base)
