"""Pruebas de lógica de PMV2/PMV3 con repositorios y Ollama simulados."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.adapters.entrada.api import (
    PracticaEntrada,
    RespuestaPracticaEntrada,
    analizar_progreso,
    generar_practica,
    responder_practica,
)
from app.application.generar_practica import validar_ejercicio
from app.application.generar_explicacion import generar_explicacion as ejecutar_explicacion
from app.adapters.salida import ollama_local
from app.adapters.salida.ollama_local import OllamaLocal
from app.domain.errores_ia import IARespuestaInvalida


EJERCICIO = {
    "enunciado": "¿Cuánto es 2 + 3?",
    "opciones": ["4", "5", "6", "7"],
    "respuesta_correcta": 1,
    "explicacion": "Al sumar dos y tres unidades se obtienen cinco unidades.",
}


class RepoConsultas:
    def asignaturas(self):
        return [{"id": 1, "nombre": "Matemática"}]


class RepoAprendizaje:
    def __init__(self):
        self.perfil = {"perfil_id": str(uuid4()), "grado": 2}
        self.practicas = {}
        self.siguiente_id = 1

    def obtener_perfil(self, perfil_id):
        return self.perfil if perfil_id == self.perfil["perfil_id"] else None

    def guardar_practica(self, datos):
        identificador = self.siguiente_id
        self.siguiente_id += 1
        self.practicas[identificador] = {
            **datos,
            "id": identificador,
            "respuesta_elegida": None,
            "correcta": None,
        }
        return identificador

    def obtener_practica(self, practica_id, perfil_id):
        practica = self.practicas.get(practica_id)
        if practica is None or practica["perfil_id"] != perfil_id:
            return None
        return practica

    def responder_practica(self, practica_id, perfil_id, opcion):
        practica = self.obtener_practica(practica_id, perfil_id)
        if practica is None:
            return None
        repetida = practica["respuesta_elegida"] is not None
        elegida = practica["respuesta_elegida"] if repetida else opcion
        correcta = elegida == practica["respuesta_correcta"]
        practica["respuesta_elegida"] = elegida
        practica["correcta"] = correcta
        return {
            "practica_id": practica_id,
            "opcion_elegida": elegida,
            "opcion_correcta": practica["respuesta_correcta"],
            "correcta": correcta,
            "explicacion": practica["explicacion"],
            "repetida": repetida,
        }

    def progreso(self, perfil_id):
        return {
            "total_consultas": 1,
            "total_practicas": 1,
            "aciertos": 0,
            "porcentaje_aciertos": 0,
            "temas": [{
                "asignatura_id": 1,
                "tema": "sumas",
                "intentos": 2,
                "porcentaje_aciertos": 0,
            }],
        }

    def historial(self, perfil_id, limite=50):
        return [{
            "tipo": "practica",
            "asignatura": "Matemática",
            "tema": "sumas",
            "detalle": "¿Cuánto es 2 + 3?",
            "estado": "PARA_REFORZAR",
            "correcta": False,
        }]


class GeneradorFalso:
    def __init__(self):
        self.grado_recibido = None
        self.dificultad_recibida = None

    def generar_ejercicio(self, *, tema, asignatura, grado, dificultad):
        self.grado_recibido = grado
        self.dificultad_recibida = dificultad
        return EJERCICIO

    def analizar_progreso(self, *, grado, progreso, historial):
        return "Refuerza las sumas y vuelve a practicar con ejemplos guiados."


def test_rechaza_ejercicio_incompleto_o_con_alternativas_duplicadas():
    with pytest.raises(IARespuestaInvalida):
        validar_ejercicio({**EJERCICIO, "opciones": ["A", "A", "B", "C"]})
    with pytest.raises(IARespuestaInvalida):
        validar_ejercicio({**EJERCICIO, "respuesta_correcta": True})


def test_generar_y_responder_practica_oculta_respuesta_y_registra_error():
    aprendizaje = RepoAprendizaje()
    generador = GeneradorFalso()
    entrada = PracticaEntrada(
        perfil_id=aprendizaje.perfil["perfil_id"],
        asignatura_id=1,
        tema="sumas",
        dificultad="basico",
    )

    ejercicio = generar_practica(entrada, RepoConsultas(), aprendizaje, generador)

    assert ejercicio["grado"] == 2
    assert "respuesta_correcta" not in ejercicio
    assert generador.grado_recibido == 2

    respuesta = responder_practica(
        ejercicio["id"],
        RespuestaPracticaEntrada(
            perfil_id=aprendizaje.perfil["perfil_id"], opcion=0
        ),
        aprendizaje,
    )
    assert respuesta["correcta"] is False
    assert respuesta["respuesta_correcta"] == "5"
    assert "Al sumar" in respuesta["explicacion"]


def test_respuesta_repetida_no_cambia_el_resultado_guardado():
    aprendizaje = RepoAprendizaje()
    ejercicio = generar_practica(
        PracticaEntrada(
            perfil_id=aprendizaje.perfil["perfil_id"],
            asignatura_id=1,
            tema="sumas",
            dificultad="reto",
        ),
        RepoConsultas(),
        aprendizaje,
        GeneradorFalso(),
    )
    datos = RespuestaPracticaEntrada(
        perfil_id=aprendizaje.perfil["perfil_id"], opcion=0
    )
    responder_practica(ejercicio["id"], datos, aprendizaje)
    repetida = responder_practica(
        ejercicio["id"], datos.model_copy(update={"opcion": 1}), aprendizaje
    )
    assert repetida["repetida"] is True
    assert repetida["opcion_elegida"] == 0
    assert repetida["correcta"] is False


def test_analisis_ia_usa_actividad_y_grado_del_perfil():
    aprendizaje = RepoAprendizaje()
    generador = GeneradorFalso()
    resultado = analizar_progreso(
        aprendizaje.perfil["perfil_id"], aprendizaje, generador
    )
    assert resultado["actividades_analizadas"] == 1
    assert "Refuerza las sumas" in resultado["orientacion"]


@pytest.mark.parametrize(
    "porcentaje, esperado",
    [(0, "basico"), (59.9, "basico"), (60, "intermedio"),
     (84.9, "intermedio"), (85, "reto"), (100, "reto")],
)
def test_dificultad_adaptativa_se_ajusta_a_los_aciertos(porcentaje, esperado):
    aprendizaje = RepoAprendizaje()
    generador = GeneradorFalso()
    original = aprendizaje.progreso
    aprendizaje.progreso = lambda perfil_id: {
        **original(perfil_id),
        "temas": [{
            "asignatura_id": 1,
            "tema": "sumas",
            "intentos": 2,
            "porcentaje_aciertos": porcentaje,
        }],
    }
    generar_practica(
        PracticaEntrada(
            perfil_id=aprendizaje.perfil["perfil_id"],
            asignatura_id=1,
            tema="sumas",
            dificultad="adaptativa",
        ),
        RepoConsultas(),
        aprendizaje,
        generador,
    )
    assert generador.dificultad_recibida == esperado


def test_no_generar_practica_para_perfil_que_no_existe():
    aprendizaje = RepoAprendizaje()
    entrada = PracticaEntrada(
        perfil_id=str(uuid4()),
        asignatura_id=1,
        tema="sumas",
        dificultad="intermedio",
    )
    with pytest.raises(HTTPException) as error:
        generar_practica(entrada, RepoConsultas(), aprendizaje, GeneradorFalso())
    assert error.value.status_code == 409


def test_ejercicio_ollama_pide_json_con_grado_y_dificultad(monkeypatch):
    monkeypatch.setattr(ollama_local, "OLLAMA_LOCAL", "http://127.0.0.1:11434")
    generador = OllamaLocal(modelo="modelo-prueba")
    capturado = {}

    def respuesta(prompt, **opciones):
        capturado["prompt"] = prompt
        capturado["opciones"] = opciones
        return '{"enunciado":"Pregunta","opciones":["A","B","C","D"],"respuesta_correcta":1,"explicacion":"Motivo"}'

    monkeypatch.setattr(generador, "_solicitar_prompt", respuesta)
    ejercicio = generador.generar_ejercicio(
        tema="fracciones",
        asignatura="Matemática",
        grado=4,
        dificultad="reto",
    )

    assert ejercicio["respuesta_correcta"] == 1
    assert "4° de secundaria" in capturado["prompt"]
    assert "DIFICULTAD: reto" in capturado["prompt"]
    assert capturado["opciones"]["formato_json"] is True


def test_explicacion_usa_el_grado_registrado():
    class Repo:
        def obtener(self, identificador):
            return {"asignatura_id": 1, "pregunta": "¿Qué es una fracción?"}

        def obtener_respuesta(self, identificador):
            return None

        def asignaturas(self):
            return [{"id": 1, "nombre": "Matemática"}]

        def guardar_respuesta(self, identificador, contenido, origen):
            return {"contenido": contenido, "origen": origen}

    class Generador:
        def generar(self, *, pregunta, asignatura, grado=None):
            assert grado == 3
            return "Una explicación para tercer grado."

    resultado = ejecutar_explicacion(Repo(), Generador(), 1, grado=3)
    assert resultado["contenido"] == "Una explicación para tercer grado."
