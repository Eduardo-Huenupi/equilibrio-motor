"""Embeddings: convierten texto en vectores para buscar por significado.

- EmbedderHash: local, gratis y determinista. Sirve para pruebas, CI y demos sin claves.
  Captura coincidencia de palabras, no sinónimos.
- EmbedderVoyage: embeddings semánticos reales por API (recomendado en producción).
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from core.texto import tokens

DIMENSION = 1024


class Embedder(Protocol):
    def embeber(self, textos: list[str], tipo: str = "documento") -> list[list[float]]: ...


class EmbedderHash:
    def __init__(self, dim: int = DIMENSION):
        self.dim = dim

    def embeber(self, textos: list[str], tipo: str = "documento") -> list[list[float]]:
        return [self._uno(t) for t in textos]

    def _uno(self, texto: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in tokens(texto):
            h = int.from_bytes(hashlib.md5(tok.encode()).digest(), "big")
            vec[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        norma = math.sqrt(sum(v * v for v in vec))
        return [v / norma for v in vec] if norma else vec


class EmbedderVoyage:
    """Cliente de Voyage AI. Requiere VOYAGE_API_KEY. No se ejecuta en las pruebas automáticas."""

    URL = "https://api.voyageai.com/v1/embeddings"

    def __init__(self, api_key: str, modelo: str = "voyage-3", lote: int = 64):
        self.api_key, self.modelo, self.lote = api_key, modelo, lote

    def embeber(self, textos: list[str], tipo: str = "documento") -> list[list[float]]:
        import httpx

        salida: list[list[float]] = []
        for i in range(0, len(textos), self.lote):
            r = httpx.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "input": textos[i : i + self.lote],
                    "model": self.modelo,
                    "input_type": "query" if tipo == "consulta" else "document",
                },
                timeout=60,
            )
            r.raise_for_status()
            salida.extend(d["embedding"] for d in r.json()["data"])
        return salida
