"""Detección de prompt injection: texto que intenta darle órdenes al modelo.

Es una primera barrera por patrones. No es infalible: por eso además el modelo recibe los
fragmentos como datos, las respuestas exigen citas y las acciones sensibles piden aprobación.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.texto import normalizar

_PATRONES = {
    "anular_instrucciones": r"(ignora|olvida|omite|desestima)\w*\s+(todas?\s+)?(tus|las|sus|mis)?\s*(instrucciones|reglas|indicaciones)",
    "anular_instrucciones_en": r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|your)\s+(instructions|rules)",
    # "actua como" solo cuenta como orden al inicio de una frase: "El profesor actúa como mediador" es texto normal.
    "cambio_de_rol": r"(ahora eres|a partir de ahora eres|finge ser|you are now|pretend to be|(?:^|[.!?:;\n]\s*)(?:actua como|act as)\b)",
    "extraer_prompt": r"(revela|muestra|repite|imprime|reveal|show|print)\w*\s+(tu|el|your|the)\s+(prompt|system prompt|mensaje de sistema|instrucciones)",
    "modo_sin_reglas": r"(modo desarrollador|developer mode|jailbreak|sin restricciones|without restrictions)",
    "etiqueta_de_sistema": r"(<\s*/?\s*system\s*>|\[\s*system\s*\]|###\s*system)",
}
_COMPILADOS = {nombre: re.compile(p) for nombre, p in _PATRONES.items()}
_INVISIBLES = re.compile("[​‌‍⁠﻿‪-‮]")


@dataclass
class Hallazgo:
    sospechoso: bool
    motivos: list[str] = field(default_factory=list)


def analizar(texto: str) -> Hallazgo:
    limpio = normalizar(_INVISIBLES.sub("", texto))
    motivos = [nombre for nombre, patron in _COMPILADOS.items() if patron.search(limpio)]
    if len(_INVISIBLES.findall(texto)) >= 3:
        motivos.append("caracteres_invisibles")
    return Hallazgo(bool(motivos), motivos)
