"""Aprobación humana: una acción sensible queda en espera hasta que una persona decide."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

ACCIONES_SENSIBLES = frozenset({
    "enviar_informe", "borrar_documento", "borrar_datos_titular",
    "contactar_paciente", "exportar_datos",
})


class AccionNoAprobada(PermissionError):
    pass


@dataclass
class Solicitud:
    id: str
    org_id: str
    solicitante: str
    accion: str
    justificacion: str
    estado: str = "pendiente"  # pendiente | aprobada | rechazada | ejecutada
    resuelta_por: str = ""


class ColaAprobaciones:
    def __init__(self) -> None:
        self._solicitudes: dict[str, Solicitud] = {}

    @staticmethod
    def requiere_aprobacion(accion: str) -> bool:
        return accion in ACCIONES_SENSIBLES

    def solicitar(self, org_id: str, solicitante: str, accion: str, justificacion: str) -> Solicitud:
        s = Solicitud(uuid.uuid4().hex, org_id, solicitante, accion, justificacion)
        self._solicitudes[s.id] = s
        return s

    def obtener(self, org_id: str, solicitud_id: str) -> Solicitud:
        s = self._solicitudes.get(solicitud_id)
        if s is None or s.org_id != org_id:
            raise KeyError("Solicitud no encontrada.")
        return s

    def pendientes(self, org_id: str) -> list[Solicitud]:
        return [s for s in self._solicitudes.values() if s.org_id == org_id and s.estado == "pendiente"]

    def resolver(self, org_id: str, solicitud_id: str, aprobador: str, aprobar: bool) -> Solicitud:
        s = self.obtener(org_id, solicitud_id)
        if s.estado != "pendiente":
            raise ValueError("La solicitud ya fue resuelta.")
        if aprobador == s.solicitante:
            raise AccionNoAprobada("Quien solicita no puede aprobar su propia acción.")
        s.estado = "aprobada" if aprobar else "rechazada"
        s.resuelta_por = aprobador
        return s

    def marcar_ejecutada(self, org_id: str, solicitud_id: str) -> Solicitud:
        """Solo se puede ejecutar lo aprobado, y una sola vez."""
        s = self.obtener(org_id, solicitud_id)
        if s.estado != "aprobada":
            raise AccionNoAprobada(f"La acción está '{s.estado}', no aprobada.")
        s.estado = "ejecutada"
        return s
