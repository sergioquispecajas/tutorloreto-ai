"""Crea la primera cuenta directiva desde una consola local segura."""

import getpass
import re
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.adapters.salida.mysql_auth_repository import MySQLAuthRepository
from app.application.seguridad import generar_hash_contrasena, validar_contrasena


def main() -> int:
    repositorio = MySQLAuthRepository()
    try:
        if repositorio.existe_directivo():
            print("Ya existe una cuenta directiva. Inicia sesión y crea las demás cuentas desde la web.")
            return 1
        correo = input("Correo del directivo: ").strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo):
            print("Escribe un correo válido.")
            return 2
        contrasena = getpass.getpass("Crea una contraseña (10 a 128 caracteres): ")
        confirmar = getpass.getpass("Confirma la contraseña: ")
        if contrasena != confirmar:
            print("Las contraseñas no coinciden.")
            return 2
        validar_contrasena(contrasena)
        usuario = repositorio.crear_usuario(
            correo=correo,
            contrasena_hash=generar_hash_contrasena(contrasena),
            rol="directivo",
            debe_cambiar=False,
        )
        print(f"Cuenta directiva creada para {usuario['correo']}. Ya puedes iniciar sesión en TutorLoreto AI.")
        return 0
    except ValueError as exc:
        print(str(exc))
        return 2
    except (SQLAlchemyError, RuntimeError):
        print("No se pudo crear la cuenta. Revisa DATABASE_URL y ejecuta sql/usuarios_login.sql en MySQL Workbench.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
