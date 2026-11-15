"""Dónde viven los fragmentos. Regla de oro: toda búsqueda filtra por org_id."""
from __future__ import annotations

import math
from collections import Counter
from typing import Protocol

from core.modelos import Fragmento, Resultado
from core.texto import tokens


class Almacen(Protocol):
    def guardar(self, fragmentos: list[Fragmento], vectores: list[list[float]]) -> None: ...
    def borrar_documento(self, org_id: str, documento_nombre: str) -> int: ...
    def buscar_vector(self, org_id: str, vector: list[float], k: int) -> list[Resultado]: ...
    def buscar_texto(self, org_id: str, consulta: str, k: int) -> list[Resultado]: ...


class AlmacenMemoria:
    """Almacén en memoria: para pruebas, evals y demos. Se pierde al reiniciar."""

    def __init__(self) -> None:
        self._filas: list[tuple[Fragmento, list[float], list[str]]] = []

    def guardar(self, fragmentos: list[Fragmento], vectores: list[list[float]]) -> None:
        for f, v in zip(fragmentos, vectores, strict=True):
            self._filas.append((f, v, tokens(f.texto)))

    def borrar_documento(self, org_id: str, documento_nombre: str) -> int:
        antes = len(self._filas)
        self._filas = [
            fila
            for fila in self._filas
            if not (fila[0].org_id == org_id and fila[0].documento_nombre == documento_nombre)
        ]
        return antes - len(self._filas)

    def _de_org(self, org_id: str):
        return [fila for fila in self._filas if fila[0].org_id == org_id]

    def buscar_vector(self, org_id: str, vector: list[float], k: int) -> list[Resultado]:
        puntuados = [
            (sum(a * b for a, b in zip(vector, v)), f) for f, v, _ in self._de_org(org_id)
        ]
        puntuados.sort(key=lambda x: x[0], reverse=True)
        return [Resultado(f, s, similitud=s) for s, f in puntuados[:k] if s > 0]

    def buscar_texto(self, org_id: str, consulta: str, k: int) -> list[Resultado]:
        """BM25 simplificado sobre las palabras del fragmento."""
        filas = self._de_org(org_id)
        if not filas:
            return []
        q = set(tokens(consulta))
        n = len(filas)
        largo_medio = sum(len(t) for _, _, t in filas) / n or 1
        df = Counter(tok for _, _, t in filas for tok in set(t) if tok in q)
        puntuados = []
        for f, _, toks in filas:
            tf = Counter(toks)
            s = 0.0
            for tok in q:
                if tf[tok]:
                    idf = math.log(1 + (n - df[tok] + 0.5) / (df[tok] + 0.5))
                    s += idf * tf[tok] * 2.2 / (tf[tok] + 1.2 * (0.25 + 0.75 * len(toks) / largo_medio))
            if s > 0:
                puntuados.append((s, f))
        puntuados.sort(key=lambda x: x[0], reverse=True)
        return [Resultado(f, s) for s, f in puntuados[:k]]


class AlmacenSupabase:
    """Almacén en Supabase (Postgres + pgvector). Usa las funciones de supabase/migrations.

    El backend se conecta con la service key; las tablas tienen RLS activado sin políticas
    públicas, así que nadie puede leerlas directo desde un navegador.
    """

    def __init__(self, url: str, service_key: str):
        from supabase import create_client

        self.db = create_client(url, service_key)

    @staticmethod
    def _vec(v: list[float]) -> str:
        return "[" + ",".join(f"{x:.6f}" for x in v) + "]"

    def guardar(self, fragmentos: list[Fragmento], vectores: list[list[float]]) -> None:
        filas = [
            {
                "id": f.id,
                "org_id": f.org_id,
                "documento_id": f.documento_id,
                "documento_nombre": f.documento_nombre,
                "pagina": f.pagina,
                "texto": f.texto,
                "embedding": self._vec(v),
            }
            for f, v in zip(fragmentos, vectores, strict=True)
        ]
        for i in range(0, len(filas), 100):
            self.db.table("motor_fragmentos").upsert(filas[i : i + 100]).execute()

    def borrar_documento(self, org_id: str, documento_nombre: str) -> int:
        r = (
            self.db.table("motor_fragmentos")
            .delete()
            .eq("org_id", org_id)
            .eq("documento_nombre", documento_nombre)
            .execute()
        )
        return len(r.data or [])

    def _a_resultados(self, filas: list[dict], con_similitud: bool) -> list[Resultado]:
        return [
            Resultado(
                Fragmento(
                    fila["id"], fila["org_id"], fila["documento_id"],
                    fila["documento_nombre"], fila["pagina"], fila["texto"],
                ),
                fila["puntaje"],
                similitud=fila["puntaje"] if con_similitud else 0.0,
            )
            for fila in filas
        ]

    def buscar_vector(self, org_id: str, vector: list[float], k: int) -> list[Resultado]:
        r = self.db.rpc(
            "motor_buscar_vector", {"p_org": org_id, "p_vec": self._vec(vector), "p_k": k}
        ).execute()
        return self._a_resultados(r.data or [], True)

    def buscar_texto(self, org_id: str, consulta: str, k: int) -> list[Resultado]:
        r = self.db.rpc(
            "motor_buscar_texto", {"p_org": org_id, "p_consulta": consulta, "p_k": k}
        ).execute()
        return self._a_resultados(r.data or [], False)
