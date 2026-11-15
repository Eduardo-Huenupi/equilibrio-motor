"""API del motor. Cada endpoint pasa por identidad -> permiso -> auditoría."""
from __future__ import annotations

import hmac
import json
import os
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from core.fabrica import crear_motor
from core.governance import ColaAprobaciones, PermisoDenegado, exigir
from core.governance.aprobaciones import AccionNoAprobada
from core.ingesta.extractores import FormatoNoSoportado
from core.motor import Motor

TAMANO_MAXIMO = 20 * 1024 * 1024
ESTATICOS = Path(__file__).parent / "static"


@dataclass(frozen=True)
class Identidad:
    org_id: str
    usuario: str
    rol: str


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=3, max_length=2000)


class SolicitudAccion(BaseModel):
    accion: str
    justificacion: str = Field(min_length=5, max_length=1000)


class Resolucion(BaseModel):
    aprobar: bool


def _claves_desde_entorno() -> dict[str, Identidad]:
    """MOTOR_API_KEYS = {"clave-larga": {"org_id": "...", "usuario": "...", "rol": "admin"}}"""
    crudo = json.loads(os.environ.get("MOTOR_API_KEYS", "{}"))
    return {clave: Identidad(**datos) for clave, datos in crudo.items()}


def crear_app(
    motor: Motor | None = None,
    cola: ColaAprobaciones | None = None,
    claves: dict[str, Identidad] | None = None,
) -> FastAPI:
    motor = motor or crear_motor()
    cola = cola or ColaAprobaciones()
    claves = claves if claves is not None else _claves_desde_entorno()
    app = FastAPI(title="equilibrio-motor", version="0.1.0")

    def identidad(x_api_key: str | None = Header(default=None)) -> Identidad:
        if x_api_key:
            for clave, ident in claves.items():
                if hmac.compare_digest(clave.encode(), x_api_key.encode()):
                    return ident
        raise HTTPException(401, "Falta una clave válida en el encabezado X-API-Key.")

    def con_permiso(permiso: str):
        def dependencia(ident: Identidad = Depends(identidad)) -> Identidad:
            try:
                exigir(ident.rol, permiso)
            except PermisoDenegado:
                motor.auditoria.registrar(
                    ident.org_id, ident.usuario, "acceso_denegado", permiso, resultado="denegado"
                )
                raise
            return ident

        return dependencia

    @app.exception_handler(PermisoDenegado)
    async def _denegado(_: Request, exc: PermisoDenegado):
        return JSONResponse({"detail": str(exc)}, status_code=403)

    @app.get("/salud")
    def salud():
        return {"estado": "ok"}

    @app.get("/", include_in_schema=False)
    def inicio():
        return FileResponse(ESTATICOS / "index.html")

    @app.post("/documentos")
    async def subir(
        archivo: UploadFile = File(...),
        ident: Identidad = Depends(con_permiso("documentos:subir")),
    ):
        contenido = await archivo.read(TAMANO_MAXIMO + 1)
        if len(contenido) > TAMANO_MAXIMO:
            raise HTTPException(413, "El archivo supera los 20 MB.")
        try:
            return motor.ingerir(ident.org_id, archivo.filename or "sin_nombre", contenido, ident.usuario)
        except FormatoNoSoportado as e:
            raise HTTPException(415, str(e)) from e

    @app.post("/preguntar")
    def preguntar(cuerpo: Pregunta, ident: Identidad = Depends(con_permiso("preguntar"))):
        return motor.preguntar(ident.org_id, cuerpo.pregunta, ident.usuario).a_dict()

    @app.get("/auditoria")
    def auditoria(ident: Identidad = Depends(con_permiso("auditoria:leer"))):
        entradas = motor.auditoria.listar(ident.org_id)
        return {
            "cadena_integra": motor.auditoria.verificar(),
            "entradas": [asdict(e) if is_dataclass(e) else e for e in entradas],
        }

    @app.post("/acciones")
    def solicitar(cuerpo: SolicitudAccion, ident: Identidad = Depends(con_permiso("acciones:solicitar"))):
        if not cola.requiere_aprobacion(cuerpo.accion):
            raise HTTPException(400, "Esa acción no está en la lista de acciones sensibles.")
        s = cola.solicitar(ident.org_id, ident.usuario, cuerpo.accion, cuerpo.justificacion)
        motor.auditoria.registrar(ident.org_id, ident.usuario, "accion_solicitada", cuerpo.accion, "pendiente")
        return asdict(s)

    @app.get("/acciones")
    def pendientes(ident: Identidad = Depends(con_permiso("acciones:resolver"))):
        return [asdict(s) for s in cola.pendientes(ident.org_id)]

    @app.post("/acciones/{solicitud_id}/resolver")
    def resolver(
        solicitud_id: str, cuerpo: Resolucion,
        ident: Identidad = Depends(con_permiso("acciones:resolver")),
    ):
        try:
            s = cola.resolver(ident.org_id, solicitud_id, ident.usuario, cuerpo.aprobar)
        except KeyError as e:
            raise HTTPException(404, "Solicitud no encontrada.") from e
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
        except AccionNoAprobada as e:
            raise HTTPException(403, str(e)) from e
        motor.auditoria.registrar(ident.org_id, ident.usuario, "accion_resuelta", s.accion, s.estado)
        return asdict(s)

    return app


def app() -> FastAPI:  # uvicorn apps.api.main:app --factory
    return crear_app()
