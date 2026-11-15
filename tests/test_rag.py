from core.modelos import Fragmento, Resultado
from core.rag.llm import NO_ENCONTRADO, Generacion
from core.rag.respuesta import responder


class LLMFijo:
    def __init__(self, texto):
        self.texto, self.llamadas = texto, 0

    def generar(self, pregunta, fragmentos):
        self.llamadas += 1
        return Generacion(self.texto, 10, 5)


def _resultados(similitud=0.9):
    f = Fragmento("f1", "org-a", "d1", "doc.txt", 3, "La nota mínima es 4,0.")
    return [Resultado(f, 0.03, similitud)]


def test_respuesta_trae_cita_con_documento_y_pagina(motor):
    r = motor.preguntar("org-a", "¿Cuál es la nota mínima de aprobación?")
    assert not r.rechazada
    assert "4,0" in r.texto
    assert (r.citas[0].documento, r.citas[0].pagina) == ("reglamento_colegio_ejemplo.txt", 2)


def test_pregunta_sin_respaldo_se_rechaza(motor):
    r = motor.preguntar("org-a", "¿Cuánto cuesta la matrícula anual?")
    assert r.rechazada and not r.citas


def test_una_organizacion_no_ve_documentos_de_otra(motor):
    r = motor.preguntar("org-b", "¿Cuál es la nota mínima de aprobación?")
    assert r.rechazada and r.recuperados == []


def test_recargar_un_documento_reemplaza_el_anterior(motor):
    motor.ingerir("org-a", "reglamento_colegio_ejemplo.txt", "La nota mínima de aprobación es 5,0.".encode())
    r = motor.preguntar("org-a", "¿Cuál es la nota mínima de aprobación?")
    assert "5,0" in r.texto and "4,0" not in r.texto


def test_sin_evidencia_no_se_llama_al_modelo():
    llm = LLMFijo("Respuesta [1]")
    r = responder(llm, "p", _resultados(similitud=0.01), umbral=0.12)
    assert r.rechazada and r.motivo == "sin_evidencia" and llm.llamadas == 0


def test_modelo_sin_respaldo_se_rechaza():
    r = responder(LLMFijo(NO_ENCONTRADO), "p", _resultados(), umbral=0.12)
    assert r.rechazada and r.motivo == "modelo_sin_respaldo"


def test_respuesta_sin_citas_se_rechaza():
    r = responder(LLMFijo("La nota mínima es 4,0."), "p", _resultados(), umbral=0.12)
    assert r.rechazada and r.motivo == "sin_citas_validas"


def test_cita_a_fragmento_inexistente_se_rechaza():
    r = responder(LLMFijo("La nota es 4,0 [1] y además 7,0 [5]."), "p", _resultados(), umbral=0.12)
    assert r.rechazada and r.motivo == "sin_citas_validas"


def test_se_registran_los_tokens_usados():
    r = responder(LLMFijo("La nota mínima es 4,0 [1]."), "p", _resultados(), umbral=0.12)
    assert (r.tokens_entrada, r.tokens_salida) == (10, 5) and r.citas[0].pagina == 3
