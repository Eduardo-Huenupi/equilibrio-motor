"""Enmascara datos personales antes de que un texto llegue a un registro."""
from __future__ import annotations

import re

_PATRONES = [
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b"), "[RUT]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[CORREO]"),
    (re.compile(r"(?<!\w)(?:\+?56\s?)?9[\s-]?\d{4}[\s-]?\d{4}\b"), "[TELEFONO]"),
]


def enmascarar(texto: str) -> str:
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto
