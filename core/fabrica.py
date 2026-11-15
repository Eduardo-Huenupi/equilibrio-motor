"""Arma el Motor según las variables de entorno. Sin claves, todo corre local en memoria."""
from __future__ import annotations

import os

from core.governance.auditoria import RegistroAuditoria, RegistroSupabase
from core.motor import Motor
from core.rag.almacen import AlmacenMemoria, AlmacenSupabase
from core.rag.embeddings import EmbedderHash, EmbedderVoyage
from core.rag.llm import LLMAnthropic, LLMExtractivo


def crear_motor() -> Motor:
    env = os.environ.get
    if env("MOTOR_ALMACEN", "memoria") == "supabase":
        url, clave = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
        almacen, auditoria = AlmacenSupabase(url, clave), RegistroSupabase(url, clave)
    else:
        almacen, auditoria = AlmacenMemoria(), RegistroAuditoria()

    if env("VOYAGE_API_KEY"):
        embedder = EmbedderVoyage(os.environ["VOYAGE_API_KEY"], env("VOYAGE_MODELO", "voyage-3"))
        umbral_defecto = "0.35"
    else:
        embedder, umbral_defecto = EmbedderHash(), "0.12"

    if env("ANTHROPIC_API_KEY"):
        llm = LLMAnthropic(os.environ["ANTHROPIC_API_KEY"], env("MOTOR_MODELO", "claude-sonnet-5-5"))
    else:
        llm = LLMExtractivo()

    return Motor(almacen, embedder, llm, auditoria, umbral=float(env("MOTOR_UMBRAL", umbral_defecto)))
