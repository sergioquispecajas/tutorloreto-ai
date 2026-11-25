"""Hash seguro de contraseñas sin dependencias externas."""

import hashlib
import hmac
import secrets


ITERACIONES = 310_000


def validar_contrasena(contrasena: str) -> None:
    if not isinstance(contrasena, str) or not 10 <= len(contrasena) <= 128:
        raise ValueError("La contraseña debe tener entre 10 y 128 caracteres.")


def generar_hash_contrasena(contrasena: str) -> str:
    validar_contrasena(contrasena)
    sal = secrets.token_bytes(16)
    derivada = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${derivada.hex()}"


def verificar_contrasena(contrasena: str, almacenada: str) -> bool:
    try:
        algoritmo, iteraciones, sal_hex, hash_hex = almacenada.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        derivada = hashlib.pbkdf2_hmac(
            "sha256", contrasena.encode("utf-8"), bytes.fromhex(sal_hex), int(iteraciones)
        )
        return hmac.compare_digest(derivada.hex(), hash_hex)
    except (AttributeError, TypeError, ValueError):
        return False
