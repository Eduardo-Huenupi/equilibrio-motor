"""Tipos de datos compartidos por todo el motor."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fragmento:
    """Un trozo de documento, siempre atado a una organización y a una página."""

    id: str
    org_id: str
    documento_id: str
    documento_nombre: str
    pagina: int
    texto: str


@dataclass
class Resultado:
    """Un fragmento recuperado por la búsqueda."""

    fragmento: Fragmento
    puntaje: float  # puntaje combinado (RRF)
    similitud: float = 0.0  # similitud coseno de la búsqueda vectorial (0 si no vino por esa vía)


@dataclass
class Cita:
    n: int
    documento: str
    pagina: int
    extracto: str


@dataclass
class Respuesta:
    texto: str
    citas: list[Cita] = field(default_factory=list)
    rechazada: bool = False
    motivo: str = ""
    latencia_ms: float = 0.0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    recuperados: list[Resultado] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {
            "respuesta": self.texto,
            "citas": [c.__dict__ for c in self.citas],
            "rechazada": self.rechazada,
            "motivo": self.motivo,
            "latencia_ms": round(self.latencia_ms, 1),
            "tokens": {"entrada": self.tokens_entrada, "salida": self.tokens_salida},
        }
