import pytest
from fastapi.testclient import TestClient

from apps.api.main import Identidad, crear_app

CLAVES = {
    "clave-admin-a": Identidad("org-a", "jefa", "admin"),
    "clave-prof-a": Identidad("org-a", "ana", "profesional"),
    "clave-lector-a": Identidad("org-a", "invitado", "lector"),
    "clave-admin-b": Identidad("org-b", "otro", "admin"),
}


def h(clave):
    return {"X-API-Key": clave}


@pytest.fixture
def cliente(motor):
    return TestClient(crear_app(motor=motor, claves=CLAVES))


def test_salud_y_pagina_de_demo(cliente):
    assert cliente.get("/salud").json() == {"estado": "ok"}
    assert "Knowledge AI" in cliente.get("/").text


@pytest.mark.parametrize("cabeceras", [{}, {"X-API-Key": "clave-falsa"}])
def test_sin_clave_valida_no_entra(cliente, cabeceras):
    assert cliente.post("/preguntar", json={"pregunta": "¿hola?"}, headers=cabeceras).status_code == 401


def test_preguntar_devuelve_citas(cliente):
    r = cliente.post("/preguntar", json={"pregunta": "¿Cuándo se realizan las reuniones de apoderados?"}, headers=h("clave-lector-a"))
    cuerpo = r.json()
    assert r.status_code == 200 and "primer martes" in cuerpo["respuesta"]
    assert cuerpo["citas"][0]["pagina"] == 4


def test_otra_organizacion_no_obtiene_respuesta(cliente):
    r = cliente.post("/preguntar", json={"pregunta": "¿Cuándo se realizan las reuniones de apoderados?"}, headers=h("clave-admin-b"))
    assert r.json()["rechazada"] and r.json()["citas"] == []


def test_lector_no_puede_subir_y_el_intento_queda_auditado(cliente):
    archivo = {"archivo": ("nuevo.txt", b"El casino abre a las 12:00 horas.", "text/plain")}
    assert cliente.post("/documentos", files=archivo, headers=h("clave-lector-a")).status_code == 403
    entradas = cliente.get("/auditoria", headers=h("clave-admin-a")).json()["entradas"]
    assert entradas[-1]["accion"] == "acceso_denegado" and entradas[-1]["usuario"] == "invitado"


def test_subir_y_luego_preguntar(cliente):
    archivo = {"archivo": ("casino.txt", "El casino abre a las 12:00 horas.".encode(), "text/plain")}
    r = cliente.post("/documentos", files=archivo, headers=h("clave-prof-a"))
    assert r.status_code == 200 and r.json()["fragmentos"] == 1
    r = cliente.post("/preguntar", json={"pregunta": "¿A qué hora abre el casino?"}, headers=h("clave-lector-a"))
    assert "12:00" in r.json()["respuesta"]


def test_formato_no_soportado(cliente):
    archivo = {"archivo": ("datos.xlsx", b"x", "application/octet-stream")}
    assert cliente.post("/documentos", files=archivo, headers=h("clave-admin-a")).status_code == 415


def test_auditoria_solo_admin_y_cadena_integra(cliente):
    cliente.post("/preguntar", json={"pregunta": "¿Cuál es la nota mínima?"}, headers=h("clave-prof-a"))
    assert cliente.get("/auditoria", headers=h("clave-prof-a")).status_code == 403
    cuerpo = cliente.get("/auditoria", headers=h("clave-admin-a")).json()
    assert cuerpo["cadena_integra"] is True
    assert all(e["org_id"] == "org-a" for e in cuerpo["entradas"])


def test_flujo_de_aprobacion_humana(cliente):
    r = cliente.post("/acciones", json={"accion": "enviar_informe", "justificacion": "informe de noviembre"}, headers=h("clave-prof-a"))
    sid = r.json()["id"]
    assert r.json()["estado"] == "pendiente"
    assert cliente.post(f"/acciones/{sid}/resolver", json={"aprobar": True}, headers=h("clave-prof-a")).status_code == 403
    assert cliente.post(f"/acciones/{sid}/resolver", json={"aprobar": True}, headers=h("clave-admin-b")).status_code == 404
    r = cliente.post(f"/acciones/{sid}/resolver", json={"aprobar": True}, headers=h("clave-admin-a"))
    assert r.json()["estado"] == "aprobada" and r.json()["resuelta_por"] == "jefa"
    assert cliente.post(f"/acciones/{sid}/resolver", json={"aprobar": False}, headers=h("clave-admin-a")).status_code == 409


def test_accion_no_sensible_no_entra_a_la_cola(cliente):
    r = cliente.post("/acciones", json={"accion": "saludar", "justificacion": "prueba simple"}, headers=h("clave-prof-a"))
    assert r.status_code == 400
