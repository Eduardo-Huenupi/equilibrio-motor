"""Registro de auditoría encadenado: si alguien altera o borra una entrada, se nota.

Cada entrada guarda el hash de la anterior (como una cadena). `verificar()` recalcula toda la
cadena y falla si algo fue modificado.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .privacidad import enmascarar

GENESIS = "0" * 64


@dataclass(frozen=True)
class Entrada:
    n: int
    momento: str
    org_id: str
    usuario: str
    accion: str
    recurso: str
    resultado: str
    detalle: str
    hash_anterior: str
    hash: str


def _hash(campos: dict) -> str:
    return hashlib.sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class RegistroAuditoria:
    """Registro en memoria. La versión en base de datos usa la tabla motor_auditoria."""

    def __init__(self) -> None:
        self._entradas: list[Entrada] = []

    def registrar(
        self, org_id: str, usuario: str, accion: str, recurso: str = "",
        resultado: str = "ok", detalle: str = "",
    ) -> Entrada:
        campos = {
            "n": len(self._entradas) + 1,
            "momento": datetime.now(timezone.utc).isoformat(),
            "org_id": org_id,
            "usuario": usuario,
            "accion": accion,
            "recurso": recurso,
            "resultado": resultado,
            "detalle": enmascarar(detalle)[:500],
            "hash_anterior": self._entradas[-1].hash if self._entradas else GENESIS,
        }
        entrada = Entrada(**campos, hash=_hash(campos))
        self._entradas.append(entrada)
        return entrada

    def listar(self, org_id: str, limite: int = 100) -> list[Entrada]:
        return [e for e in self._entradas if e.org_id == org_id][-limite:]

    def verificar(self) -> bool:
        anterior = GENESIS
        for e in self._entradas:
            campos = asdict(e)
            hash_guardado = campos.pop("hash")
            if e.hash_anterior != anterior or _hash(campos) != hash_guardado:
                return False
            anterior = hash_guardado
        return True


class RegistroSupabase:
    """Registro en Supabase. El encadenado y el bloqueo de cambios los hace la base de datos."""

    def __init__(self, url: str, service_key: str):
        from supabase import create_client

        self.db = create_client(url, service_key)

    def registrar(
        self, org_id: str, usuario: str, accion: str, recurso: str = "",
        resultado: str = "ok", detalle: str = "",
    ) -> None:
        self.db.table("motor_auditoria").insert({
            "org_id": org_id, "usuario": usuario, "accion": accion, "recurso": recurso,
            "resultado": resultado, "detalle": enmascarar(detalle)[:500],
        }).execute()

    def listar(self, org_id: str, limite: int = 100) -> list[dict]:
        r = (
            self.db.table("motor_auditoria").select("*").eq("org_id", org_id)
            .order("n", desc=True).limit(limite).execute()
        )
        return list(reversed(r.data or []))

    def verificar(self) -> bool:
        return bool(self.db.rpc("motor_verificar_auditoria", {}).execute().data)
