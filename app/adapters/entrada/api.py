"""Adaptador HTTP: entrega entrada al caso de uso y traduce errores a HTTP."""
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.application.registrar_consulta import registrar_consulta
from app.application.generar_explicacion import generar_explicacion
from app.application.generar_practica import validar_ejercicio
from app.adapters.salida.mysql_repository import MySQLConsultaRepository
from app.adapters.salida.mysql_aprendizaje_repository import MySQLAprendizajeRepository
from app.adapters.salida.ollama_local import OllamaLocal
from app.adapters.entrada.auth_api import obtener_usuario_actual
from app.ports.consulta_repository import ConsultaRepository
from app.ports.aprendizaje_repository import AprendizajeRepository
from app.ports.generador_explicaciones import GeneradorExplicaciones
from app.domain.errores_ia import (
    IANoDisponible, IATiempoAgotado, IARespuestaInvalida, ConsultaNoEncontrada,
)

router = APIRouter()


def exigir_perfil_alumno(usuario: dict, perfil_solicitado: str | UUID | None = None) -> str:
    if usuario.get("rol") != "alumno" or not usuario.get("perfil_id"):
        raise HTTPException(403, "Esta función está disponible para cuentas de alumno.")
    perfil_id = str(usuario["perfil_id"])
    if perfil_solicitado is not None and str(perfil_solicitado) != perfil_id:
        raise HTTPException(403, "No puedes consultar el progreso de otra cuenta.")
    return perfil_id


def obtener_repositorio() -> ConsultaRepository:
    """Punto de inyección. Permite sustituir MySQL en las pruebas."""
    return MySQLConsultaRepository()


def obtener_aprendizaje_repository() -> AprendizajeRepository:
    """Punto de inyección de perfiles, prácticas e historial."""
    return MySQLAprendizajeRepository()


class ConsultaEntrada(BaseModel):
    asignatura_id: int = Field(ge=1)
    pregunta: str = Field(min_length=1, max_length=2000)
    perfil_id: UUID | None = None


class ExplicacionEntrada(BaseModel):
    perfil_id: UUID | None = None


class PerfilEntrada(BaseModel):
    grado: int = Field(ge=1, le=5)


class PracticaEntrada(BaseModel):
    perfil_id: UUID
    asignatura_id: int = Field(ge=1)
    tema: str = Field(min_length=2, max_length=180)
    dificultad: Literal["adaptativa", "basico", "intermedio", "reto"]


class PracticaBibliotecaEntrada(BaseModel):
    perfil_id: UUID
    asignatura_id: int = Field(ge=1)
    tema: str = Field(min_length=2, max_length=180)
    enunciado: str = Field(min_length=1, max_length=1200)
    opciones: list[str]
    respuesta_correcta: int = Field(ge=0, le=3)
    explicacion: str = Field(min_length=1, max_length=2500)
    opcion: int = Field(ge=0, le=3)


class RespuestaPracticaEntrada(BaseModel):
    perfil_id: UUID
    opcion: int = Field(ge=0, le=3)


@router.get('/asignaturas')
def listar_asignaturas(repo: ConsultaRepository = Depends(obtener_repositorio)):
    try:
        return repo.asignaturas()
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, 'La base de datos no está disponible.')


@router.post('/consultas', status_code=201)
def crear_consulta(
    datos: ConsultaEntrada,
    repo: ConsultaRepository = Depends(obtener_repositorio),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id = exigir_perfil_alumno(usuario, datos.perfil_id)
        return registrar_consulta(
            repo,
            datos.asignatura_id,
            datos.pregunta,
            perfil_id,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, 'No se pudo registrar la consulta en la base de datos.')


@router.get('/consultas/{identificador}')
def buscar_consulta(
    identificador: int,
    repo: ConsultaRepository = Depends(obtener_repositorio),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        consulta = repo.obtener(identificador)
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, 'No se pudo consultar la base de datos.')
    if consulta is None:
        raise HTTPException(404, 'Consulta no encontrada.')
    perfil_id = exigir_perfil_alumno(usuario)
    if consulta.get("perfil_id") != perfil_id:
        raise HTTPException(404, 'Consulta no encontrada.')
    consulta.pop("perfil_id", None)
    return consulta


# -------- HU-IA01 + HU04: IA educativa ejecutada en el propio ordenador --------
def obtener_generador() -> GeneradorExplicaciones:
    """Inyectable: reemplazar por un generador falso en pruebas sin Ollama."""
    return OllamaLocal()


@router.get('/ia/estado')
def estado_ia():
    """Informa si el motor y modelo locales están listos."""
    try:
        return OllamaLocal().estado()
    except IANoDisponible as exc:
        return {'disponible': False, 'modelo': '-', 'detalle': str(exc)}


@router.post('/consultas/{identificador}/explicacion')
def crear_explicacion(
    identificador: int,
    datos: ExplicacionEntrada | None = Body(default=None),
    repo: ConsultaRepository = Depends(obtener_repositorio),
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    generador: GeneradorExplicaciones = Depends(obtener_generador),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id = exigir_perfil_alumno(usuario, datos.perfil_id if datos else None)
        consulta = repo.obtener(identificador)
        if consulta is None or consulta.get("perfil_id") != perfil_id:
            raise HTTPException(404, "Consulta no encontrada.")
        perfil = aprendizaje.obtener_perfil(perfil_id)
        if perfil is None:
            raise HTTPException(404, "No encontramos el perfil de aprendizaje.")
        grado = int(perfil["grado"])
        return generar_explicacion(repo, generador, identificador, grado=grado)
    except ConsultaNoEncontrada as exc:
        raise HTTPException(404, str(exc)) from exc
    except IATiempoAgotado as exc:
        raise HTTPException(504, str(exc)) from exc
    except IANoDisponible as exc:
        raise HTTPException(503, str(exc)) from exc
    except IARespuestaInvalida as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, 'La base de datos no está disponible.') from exc


# -------- PMV 2: perfil por grado y práctica personalizada --------

@router.put("/perfiles/{perfil_id}")
def guardar_perfil(
    perfil_id: UUID,
    datos: PerfilEntrada,
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id_propio = exigir_perfil_alumno(usuario, perfil_id)
        perfil = aprendizaje.obtener_perfil(perfil_id_propio)
        if perfil is None:
            raise HTTPException(404, "No encontramos el perfil de aprendizaje.")
        if int(perfil["grado"]) != datos.grado:
            raise HTTPException(403, "El grado lo asigna el directivo o docente del colegio.")
        return perfil
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo guardar el perfil de aprendizaje.") from exc


@router.get("/perfiles/{perfil_id}")
def consultar_perfil(
    perfil_id: UUID,
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id_propio = exigir_perfil_alumno(usuario, perfil_id)
        perfil = aprendizaje.obtener_perfil(perfil_id_propio)
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo consultar el perfil de aprendizaje.") from exc
    if perfil is None:
        raise HTTPException(404, "Todavía no registraste tu grado.")
    return perfil


@router.post("/practicas/generar", status_code=201)
def generar_practica(
    datos: PracticaEntrada,
    repo: ConsultaRepository = Depends(obtener_repositorio),
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    generador: OllamaLocal = Depends(obtener_generador),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id = exigir_perfil_alumno(usuario, datos.perfil_id)
        tema = datos.tema.strip()
        if len(tema) < 2:
            raise HTTPException(422, "Escribe un tema de al menos dos caracteres.")
        perfil = aprendizaje.obtener_perfil(perfil_id)
        if perfil is None:
            raise HTTPException(409, "Registra primero tu grado de secundaria.")
        materia = next(
            (item["nombre"] for item in repo.asignaturas()
             if item["id"] == datos.asignatura_id),
            None,
        )
        if not materia:
            raise HTTPException(422, "La asignatura indicada no existe.")

        dificultad = datos.dificultad
        if dificultad == "adaptativa":
            avance = aprendizaje.progreso(perfil_id)
            tema_actual = tema.casefold()
            registro = next((item for item in avance.get("temas", [])
                             if item.get("asignatura_id") == datos.asignatura_id
                             and str(item.get("tema", "")).casefold() == tema_actual), None)
            if registro is None or not registro.get("intentos"):
                dificultad = "basico"
            elif float(registro["porcentaje_aciertos"]) < 60:
                dificultad = "basico"
            elif float(registro["porcentaje_aciertos"]) < 85:
                dificultad = "intermedio"
            else:
                dificultad = "reto"

        ejercicio = validar_ejercicio(generador.generar_ejercicio(
            tema=tema,
            asignatura=materia,
            grado=int(perfil["grado"]),
            dificultad=dificultad,
        ))
        practica_id = aprendizaje.guardar_practica({
            "perfil_id": perfil_id,
            "asignatura_id": datos.asignatura_id,
            "tema": tema,
            "dificultad": dificultad,
            **ejercicio,
        })
        # La respuesta correcta queda en MySQL y se revela solo al responder.
        return {
            "id": practica_id,
            "asignatura": materia,
            "tema": tema,
            "dificultad": dificultad,
            "grado": int(perfil["grado"]),
            "enunciado": ejercicio["enunciado"],
            "opciones": ejercicio["opciones"],
        }
    except IATiempoAgotado as exc:
        raise HTTPException(504, str(exc)) from exc
    except IANoDisponible as exc:
        raise HTTPException(503, str(exc)) from exc
    except IARespuestaInvalida as exc:
        raise HTTPException(502, str(exc)) from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo guardar la práctica en MySQL.") from exc


@router.post("/practicas/biblioteca", status_code=201)
def responder_practica_precargada(
    datos: PracticaBibliotecaEntrada,
    repo: ConsultaRepository = Depends(obtener_repositorio),
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Guarda en el historial la respuesta a un ejercicio estático de la biblioteca."""
    try:
        perfil_id = exigir_perfil_alumno(usuario, datos.perfil_id)
        if aprendizaje.obtener_perfil(perfil_id) is None:
            raise HTTPException(409, "Registra primero tu grado para guardar esta práctica.")
        existe_asignatura = any(
            item["id"] == datos.asignatura_id for item in repo.asignaturas()
        )
        if not existe_asignatura:
            raise HTTPException(422, "La asignatura indicada no existe.")
        ejercicio = validar_ejercicio({
            "enunciado": datos.enunciado,
            "opciones": datos.opciones,
            "respuesta_correcta": datos.respuesta_correcta,
            "explicacion": datos.explicacion,
        })
        if datos.opcion >= len(ejercicio["opciones"]):
            raise HTTPException(422, "Selecciona una alternativa válida.")
        practica_id = aprendizaje.guardar_practica({
            "perfil_id": perfil_id,
            "asignatura_id": datos.asignatura_id,
            "tema": datos.tema.strip(),
            "dificultad": "basico",
            **ejercicio,
        })
        resultado = aprendizaje.responder_practica(
            practica_id, perfil_id, datos.opcion
        )
        if resultado is None:
            raise HTTPException(500, "No se pudo registrar la respuesta.")
        resultado["respuesta_correcta"] = ejercicio["opciones"][
            resultado["opcion_correcta"]
        ]
        resultado["tema"] = datos.tema.strip()
        return resultado
    except IARespuestaInvalida as exc:
        raise HTTPException(422, str(exc)) from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo guardar tu respuesta en el historial.") from exc


@router.post("/practicas/{practica_id}/respuesta")
def responder_practica(
    practica_id: int,
    datos: RespuestaPracticaEntrada,
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id = exigir_perfil_alumno(usuario, datos.perfil_id)
        practica = aprendizaje.obtener_practica(practica_id, perfil_id)
        if practica is None:
            raise HTTPException(404, "No encontramos este ejercicio.")
        if datos.opcion >= len(practica["opciones"]):
            raise HTTPException(422, "Selecciona una alternativa del ejercicio.")
        resultado = aprendizaje.responder_practica(
            practica_id, perfil_id, datos.opcion
        )
        if resultado is None:
            raise HTTPException(404, "No encontramos este ejercicio.")
        resultado["respuesta_correcta"] = practica["opciones"][
            resultado["opcion_correcta"]
        ]
        return resultado
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo guardar tu respuesta.") from exc


# -------- PMV 3: historial, progreso temático y orientación con IA --------

@router.get("/perfiles/{perfil_id}/historial")
def consultar_historial(
    perfil_id: UUID,
    limite: int = Query(default=50, ge=1, le=100),
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id_propio = exigir_perfil_alumno(usuario, perfil_id)
        return {"actividades": aprendizaje.historial(perfil_id_propio, limite)}
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo consultar el historial.") from exc


@router.get("/perfiles/{perfil_id}/progreso")
def consultar_progreso(
    perfil_id: UUID,
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id_propio = exigir_perfil_alumno(usuario, perfil_id)
        return aprendizaje.progreso(perfil_id_propio)
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo calcular el progreso.") from exc


@router.post("/perfiles/{perfil_id}/analisis")
def analizar_progreso(
    perfil_id: UUID,
    aprendizaje: AprendizajeRepository = Depends(obtener_aprendizaje_repository),
    generador: OllamaLocal = Depends(obtener_generador),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        perfil_id_propio = exigir_perfil_alumno(usuario, perfil_id)
        perfil = aprendizaje.obtener_perfil(perfil_id_propio)
        if perfil is None:
            raise HTTPException(404, "No encontramos el perfil de aprendizaje.")
        progreso = aprendizaje.progreso(perfil_id_propio)
        if not progreso.get("total_practicas"):
            raise HTTPException(
                422,
                "Resuelve al menos una práctica antes de analizar tus temas por reforzar.",
            )
        historial = aprendizaje.historial(perfil_id_propio, 30)
        if not historial:
            raise HTTPException(422, "Realiza una consulta o práctica antes del análisis.")
        historial_resumido = [
            {
                "tipo": item["tipo"],
                "asignatura": item["asignatura"],
                "tema": item["tema"],
                "detalle": str(item["detalle"])[:240],
                "estado": item["estado"],
            }
            for item in historial
        ]
        orientacion = generador.analizar_progreso(
            grado=int(perfil["grado"]),
            progreso=progreso,
            historial=historial_resumido,
        )
        return {"orientacion": orientacion, "actividades_analizadas": len(historial)}
    except IATiempoAgotado as exc:
        raise HTTPException(504, str(exc)) from exc
    except IANoDisponible as exc:
        raise HTTPException(503, str(exc)) from exc
    except IARespuestaInvalida as exc:
        raise HTTPException(502, str(exc)) from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo analizar el historial.") from exc


@router.get('/consultas/{identificador}/respuesta')
def consultar_explicacion(
    identificador: int,
    repo: ConsultaRepository = Depends(obtener_repositorio),
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        consulta = repo.obtener(identificador)
        if consulta is None:
            raise HTTPException(404, 'Consulta no encontrada.')
        perfil_id = exigir_perfil_alumno(usuario)
        if consulta.get("perfil_id") != perfil_id:
            raise HTTPException(404, 'Consulta no encontrada.')
        respuesta = repo.obtener_respuesta(identificador)
        if respuesta is None:
            raise HTTPException(404, 'La consulta todavía no tiene explicación.')
        return respuesta
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, 'La base de datos no está disponible.') from exc


@router.get('/estado')
def estado_servidor():
    """Comprobación local del servidor; no acredita acceso LAN ni Internet externo."""
    return {'servidor': 'disponible', 'modo': 'local',
            'detalle': 'Respuesta del servidor TutorLoreto AI.'}

# -------- PoC S9: predicción local de refuerzo académico --------

from app.application.analizar_desempeno import analizar_desempeno
from app.adapters.salida.modelo_refuerzo_local import ModeloRefuerzoLocal
from app.ports.predictor_refuerzo import PredictorRefuerzo


class DesempenoEntrada(BaseModel):
    grado: int = Field(ge=1, le=5)
    porcentaje_aciertos: float = Field(ge=0, le=100)
    respuestas_incorrectas: int = Field(ge=0, le=8)
    tiempo_promedio_segundos: float = Field(ge=10, le=180)
    temas_con_error: int = Field(ge=0, le=6)
    intentos_previos: int = Field(ge=0, le=8)


def obtener_predictor() -> PredictorRefuerzo:
    return ModeloRefuerzoLocal()


@router.post("/prediccion/refuerzo")
def predecir_refuerzo(
    datos: DesempenoEntrada,
    predictor: PredictorRefuerzo = Depends(obtener_predictor),
):
    from app.adapters.salida.mysql_practicas_predictivas import (
        MySQLPracticaPredictivaRepository,
    )

    try:
        # 1. Validar los datos y ejecutar Random Forest.
        datos_validados = datos.model_dump()
        resultado = analizar_desempeno(predictor, datos_validados)

        # 2. Guardar la práctica y su predicción en MySQL.
        repositorio = MySQLPracticaPredictivaRepository()
        identificador = repositorio.registrar(
            datos_validados,
            resultado,
        )

        # 3. Devolver el resultado junto con el ID guardado.
        return {
            **resultado,
            "practica_id": identificador,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudo guardar la práctica en MySQL.",
        ) from exc

