"""El Motor une las piezas: ingesta -> búsqueda -> respuesta con citas, con governance en cada paso."""
from __future__ import annotations

import hashlib
import time

from core.governance import analizar
from core.ingesta import extraer_paginas, fragmentar
from core.modelos import Fragmento, Respuesta
from core.rag.almacen import Almacen
from core.rag.buscador import buscar
from core.rag.embeddings import Embedder
from core.rag.llm import LLM
from core.rag.respuesta import responder


class Motor:
    def __init__(
        self, almacen: Almacen, embedder: Embedder, llm: LLM, auditoria,
        umbral: float = 0.12, k: int = 8,
    ):
        self.almacen, self.embedder, self.llm, self.auditoria = almacen, embedder, llm, auditoria
        self.umbral, self.k = umbral, k

    def ingerir(self, org_id: str, nombre: str, contenido: bytes, usuario: str = "sistema") -> dict:
        """Carga un documento. Si ya existía uno con ese nombre en la organización, lo reemplaza."""
        paginas = extraer_paginas(nombre, contenido)
        documento_id = hashlib.sha256(org_id.encode() + b"|" + contenido).hexdigest()[:16]
        fragmentos, bloqueados = [], 0
        for i, (pagina, texto) in enumerate(fragmentar(paginas)):
            if analizar(texto).sospechoso:
                bloqueados += 1  # no se indexa texto que intenta darle órdenes al modelo
                continue
            fragmentos.append(
                Fragmento(f"{documento_id}-{i}", org_id, documento_id, nombre, pagina, texto)
            )
        self.almacen.borrar_documento(org_id, nombre)
        if fragmentos:
            vectores = self.embedder.embeber([f.texto for f in fragmentos], tipo="documento")
            self.almacen.guardar(fragmentos, vectores)
        resumen = {
            "documento_id": documento_id, "nombre": nombre, "paginas": len(paginas),
            "fragmentos": len(fragmentos), "fragmentos_bloqueados": bloqueados,
        }
        self.auditoria.registrar(
            org_id, usuario, "documento_cargado", nombre,
            detalle=f"{len(fragmentos)} fragmentos, {bloqueados} bloqueados",
        )
        return resumen

    def preguntar(self, org_id: str, pregunta: str, usuario: str = "sistema") -> Respuesta:
        inicio = time.perf_counter()
        hallazgo = analizar(pregunta)
        if hallazgo.sospechoso:
            r = Respuesta(
                "No puedo procesar esa solicitud.", rechazada=True, motivo="entrada_bloqueada"
            )
            self.auditoria.registrar(
                org_id, usuario, "pregunta", resultado="bloqueada",
                detalle=f"motivos={','.join(hallazgo.motivos)} | {pregunta}",
            )
        else:
            resultados = buscar(self.almacen, self.embedder, org_id, pregunta, self.k)
            r = responder(self.llm, pregunta, resultados, self.umbral)
            fuentes = ", ".join(f"{c.documento} p.{c.pagina}" for c in r.citas)
            self.auditoria.registrar(
                org_id, usuario, "pregunta",
                resultado=f"rechazada:{r.motivo}" if r.rechazada else "respondida",
                detalle=f"{pregunta} | fuentes: {fuentes or 'ninguna'}",
            )
        r.latencia_ms = (time.perf_counter() - inicio) * 1000
        return r
