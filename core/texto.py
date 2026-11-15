"""Normalización de texto en español, compartida por embeddings locales, búsqueda y evals."""
from __future__ import annotations

import re
import unicodedata

_VACIAS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "a", "en", "que",
    "cual", "cuales", "como", "cuando", "quien", "quienes", "donde", "se", "es", "son", "por",
    "para", "con", "sin", "del", "al", "lo", "le", "les", "su", "sus", "si", "no", "puede",
    "pueden", "debe", "deben", "cada", "cuanto", "cuantos", "cuanta", "cuantas", "hay", "ser",
    "esta", "este", "estos", "estas", "mas", "ya", "muy", "tambien", "solo", "me", "mi", "tu",
}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Suspensión' -> 'suspension'."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _raiz(palabra: str) -> str:
    """Raíz muy simple: quita plural y 'e' final ('estudiantes' y 'estudiante' -> 'estudiant')."""
    if len(palabra) > 3 and palabra.endswith("s"):
        palabra = palabra[:-1]
    if len(palabra) > 4 and palabra.endswith("e"):
        palabra = palabra[:-1]
    return palabra


def tokens(texto: str) -> list[str]:
    palabras = re.findall(r"[a-z0-9]+", normalizar(texto))
    return [_raiz(p) for p in palabras if len(p) > 1 and p not in _VACIAS]


def oraciones(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?])\s+", texto.strip())
    return [p.strip() for p in partes if p.strip()]
