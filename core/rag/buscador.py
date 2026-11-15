"""Búsqueda híbrida: por significado (vector) + por palabras, combinadas con RRF."""
from __future__ import annotations

from core.modelos import Resultado

from .almacen import Almacen
from .embeddings import Embedder

_RRF_K = 60


def buscar(
    almacen: Almacen, embedder: Embedder, org_id: str, consulta: str, k: int = 8
) -> list[Resultado]:
    """Reciprocal Rank Fusion: un fragmento sube si aparece arriba en cualquiera de las dos listas."""
    amplitud = max(k * 3, 20)
    vector = embedder.embeber([consulta], tipo="consulta")[0]
    por_vector = almacen.buscar_vector(org_id, vector, amplitud)
    por_texto = almacen.buscar_texto(org_id, consulta, amplitud)

    combinado: dict[str, Resultado] = {}
    for lista in (por_vector, por_texto):
        for puesto, r in enumerate(lista, 1):
            actual = combinado.get(r.fragmento.id)
            if actual is None:
                actual = combinado[r.fragmento.id] = Resultado(r.fragmento, 0.0, 0.0)
            actual.puntaje += 1 / (_RRF_K + puesto)
            actual.similitud = max(actual.similitud, r.similitud)
    return sorted(combinado.values(), key=lambda r: r.puntaje, reverse=True)[:k]
