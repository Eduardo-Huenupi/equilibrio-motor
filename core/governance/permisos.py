"""Roles y permisos. Todo lo que no está permitido explícitamente está prohibido."""
from __future__ import annotations

ROLES: dict[str, frozenset[str]] = {
    "admin": frozenset({
        "preguntar", "documentos:subir", "documentos:borrar", "auditoria:leer",
        "acciones:solicitar", "acciones:resolver", "titulares:gestionar",
    }),
    "profesional": frozenset({"preguntar", "documentos:subir", "acciones:solicitar"}),
    "lector": frozenset({"preguntar"}),
}


class PermisoDenegado(PermissionError):
    pass


def puede(rol: str, permiso: str) -> bool:
    return permiso in ROLES.get(rol, frozenset())


def exigir(rol: str, permiso: str) -> None:
    if not puede(rol, permiso):
        raise PermisoDenegado(f"El rol '{rol}' no tiene el permiso '{permiso}'.")
