"""Inicio de sesión y administración de cuentas escolares en la red local."""

import hashlib
import os
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.adapters.salida.mysql_auth_repository import MySQLAuthRepository
from app.application.seguridad import generar_hash_contrasena, validar_contrasena, verificar_contrasena


router = APIRouter()
COOKIE_SESION = "tutorloreto_session"
DURACION_SESION_HORAS = 12
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().lower() in {
    "1", "true", "yes", "on"
}


def obtener_repositorio_auth() -> MySQLAuthRepository:
    return MySQLAuthRepository()


class InicioSesionEntrada(BaseModel):
    correo: str = Field(min_length=5, max_length=254)
    contrasena: str = Field(min_length=1, max_length=128)


class CambioContrasenaEntrada(BaseModel):
    contrasena_actual: str = Field(min_length=1, max_length=128)
    contrasena_nueva: str = Field(min_length=10, max_length=128)


class CrearCuentaEntrada(BaseModel):
    correo: str = Field(min_length=5, max_length=254)
    contrasena_temporal: str = Field(min_length=10, max_length=128)
    rol: Literal["alumno", "docente"] = "alumno"
    grado: int | None = Field(default=None, ge=1, le=5)
    vigente_hasta: date | None = None


def obtener_usuario_actual(
    request: Request,
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
) -> dict:
    token = request.cookies.get(COOKIE_SESION)
    if not token:
        raise HTTPException(401, "Inicia sesión para continuar.")
    usuario = repositorio.usuario_por_sesion(hashlib.sha256(token.encode("utf-8")).hexdigest())
    if usuario is None:
        raise HTTPException(401, "La sesión venció. Inicia sesión nuevamente.")
    return usuario


def exigir_personal(usuario: dict) -> None:
    if usuario["rol"] not in {"directivo", "docente"}:
        raise HTTPException(403, "Solo directivos y docentes pueden administrar cuentas.")


def usuario_publico(usuario: dict) -> dict:
    return {
        "id": usuario["id"],
        "correo": usuario["correo"],
        "rol": usuario["rol"],
        "perfil_id": usuario["perfil_id"],
        "grado": usuario["grado"],
        "vigente_hasta": usuario["vigente_hasta"],
        "debe_cambiar_contrasena": usuario["debe_cambiar_contrasena"],
    }


def _correo_normalizado(correo: str) -> str:
    correo = correo.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo):
        raise HTTPException(422, "Escribe un correo válido.")
    return correo


@router.post("/login")
def iniciar_sesion(
    datos: InicioSesionEntrada,
    respuesta: Response,
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
):
    try:
        usuario = repositorio.buscar_por_correo(_correo_normalizado(datos.correo))
        if usuario is None or not verificar_contrasena(
            datos.contrasena, usuario["contrasena_hash"] or ""
        ):
            raise HTTPException(401, "Correo o contraseña incorrectos.")
        if not usuario["activo"]:
            raise HTTPException(403, "La cuenta está desactivada. Consulta con el colegio.")
        if usuario["vigente_hasta"] and date.fromisoformat(usuario["vigente_hasta"]) < date.today():
            raise HTTPException(403, "La vigencia de esta cuenta terminó. Consulta con el colegio.")

        token = secrets.token_urlsafe(32)
        vence_en = datetime.now() + timedelta(hours=DURACION_SESION_HORAS)
        repositorio.guardar_sesion(
            usuario["id"], hashlib.sha256(token.encode("utf-8")).hexdigest(), vence_en
        )
        respuesta.set_cookie(
            key=COOKIE_SESION,
            value=token,
            max_age=DURACION_SESION_HORAS * 60 * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            path="/",
        )
        return {"usuario": usuario_publico(usuario)}
    except HTTPException:
        raise
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo iniciar sesión. Revisa la base de datos escolar.") from exc


@router.get("/me")
def consultar_sesion(usuario: dict = Depends(obtener_usuario_actual)):
    return {"usuario": usuario_publico(usuario)}


@router.post("/logout")
def cerrar_sesion(
    request: Request,
    respuesta: Response,
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
):
    token = request.cookies.get(COOKIE_SESION)
    try:
        if token:
            repositorio.cerrar_sesion(hashlib.sha256(token.encode("utf-8")).hexdigest())
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo cerrar la sesión en el servidor.") from exc
    respuesta.delete_cookie(
        COOKIE_SESION,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return {"cerrada": True}


@router.put("/contrasena")
def cambiar_contrasena(
    datos: CambioContrasenaEntrada,
    usuario: dict = Depends(obtener_usuario_actual),
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
):
    try:
        cuenta = repositorio.buscar_por_correo(usuario["correo"])
        if cuenta is None or not verificar_contrasena(
            datos.contrasena_actual, cuenta["contrasena_hash"] or ""
        ):
            raise HTTPException(422, "La contraseña actual no coincide.")
        if datos.contrasena_actual == datos.contrasena_nueva:
            raise HTTPException(422, "Elige una contraseña diferente a la actual.")
        nuevo_hash = generar_hash_contrasena(datos.contrasena_nueva)
        repositorio.cambiar_contrasena(usuario["id"], nuevo_hash)
        return {"actualizada": True}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo actualizar la contraseña.") from exc


@router.get("/cuentas")
def listar_cuentas(
    usuario: dict = Depends(obtener_usuario_actual),
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
):
    exigir_personal(usuario)
    try:
        return {"cuentas": repositorio.listar_cuentas()}
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo cargar la lista de cuentas.") from exc


@router.post("/cuentas", status_code=201)
def crear_cuenta(
    datos: CrearCuentaEntrada,
    usuario: dict = Depends(obtener_usuario_actual),
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
):
    exigir_personal(usuario)
    correo = _correo_normalizado(datos.correo)
    if usuario["rol"] == "docente" and datos.rol != "alumno":
        raise HTTPException(403, "El personal docente puede crear cuentas de alumnos.")
    if datos.rol == "alumno":
        if datos.grado is None:
            raise HTTPException(422, "Selecciona el grado del alumno.")
        if datos.vigente_hasta is None or datos.vigente_hasta < date.today():
            raise HTTPException(422, "Indica una fecha de vigencia futura para el alumno.")
    elif datos.grado is not None:
        raise HTTPException(422, "Las cuentas de docente no usan grado de alumno.")
    try:
        cuenta = repositorio.crear_usuario(
            correo=correo,
            contrasena_hash=generar_hash_contrasena(datos.contrasena_temporal),
            rol=datos.rol,
            grado=datos.grado,
            vigente_hasta=datos.vigente_hasta,
            debe_cambiar=True,
        )
        return {"cuenta": cuenta}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Ya existe una cuenta con ese correo.") from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo crear la cuenta en MySQL.") from exc


@router.post("/cuentas/{usuario_id}/desactivar")
def desactivar_cuenta(
    usuario_id: str,
    usuario: dict = Depends(obtener_usuario_actual),
    repositorio: MySQLAuthRepository = Depends(obtener_repositorio_auth),
):
    exigir_personal(usuario)
    try:
        if not repositorio.desactivar(usuario_id):
            raise HTTPException(404, "No se encontró una cuenta de alumno activa.")
        return {"desactivada": True}
    except HTTPException:
        raise
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo desactivar la cuenta.") from exc
