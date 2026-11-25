"""Persistencia de cuentas escolares y sesiones locales."""

import uuid

from sqlalchemy import text

from app.infrastructure.database import get_engine


class MySQLAuthRepository:
    def buscar_por_correo(self, correo: str) -> dict | None:
        with get_engine().connect() as conexion:
            fila = conexion.execute(text("""
                SELECT u.id, u.correo, u.contrasena_hash, u.rol, u.perfil_id,
                       u.vigente_hasta, u.activo, u.debe_cambiar_contrasena,
                       p.grado
                FROM usuarios u
                LEFT JOIN perfiles_estudio p ON p.id = u.perfil_id
                WHERE u.correo = :correo
            """), {"correo": correo}).mappings().first()
        return self._usuario(fila) if fila else None

    def crear_usuario(
        self,
        correo: str,
        contrasena_hash: str,
        rol: str,
        grado: int | None = None,
        vigente_hasta=None,
        debe_cambiar: bool = True,
    ) -> dict:
        if rol not in {"directivo", "docente", "alumno"}:
            raise ValueError("El tipo de cuenta no es válido.")
        usuario_id = str(uuid.uuid4())
        perfil_id = str(uuid.uuid4()) if rol == "alumno" else None
        with get_engine().begin() as conexion:
            if perfil_id:
                if not isinstance(grado, int) or not 1 <= grado <= 5:
                    raise ValueError("El grado del alumno debe estar entre 1 y 5.")
                conexion.execute(text("""
                    INSERT INTO perfiles_estudio (id, grado) VALUES (:id, :grado)
                """), {"id": perfil_id, "grado": grado})
            conexion.execute(text("""
                INSERT INTO usuarios (
                    id, correo, contrasena_hash, rol, perfil_id,
                    vigente_hasta, activo, debe_cambiar_contrasena
                ) VALUES (
                    :id, :correo, :hash, :rol, :perfil_id,
                    :vigencia, 1, :debe_cambiar
                )
            """), {
                "id": usuario_id,
                "correo": correo,
                "hash": contrasena_hash,
                "rol": rol,
                "perfil_id": perfil_id,
                "vigencia": vigente_hasta,
                "debe_cambiar": debe_cambiar,
            })
        return {
            "id": usuario_id,
            "correo": correo,
            "rol": rol,
            "perfil_id": perfil_id,
            "grado": grado if rol == "alumno" else None,
            "vigente_hasta": vigente_hasta.isoformat() if vigente_hasta else None,
            "debe_cambiar_contrasena": debe_cambiar,
        }

    def guardar_sesion(self, usuario_id: str, token_hash: str, vence_en) -> None:
        with get_engine().begin() as conexion:
            conexion.execute(text("DELETE FROM sesiones WHERE vence_en < CURRENT_TIMESTAMP"))
            conexion.execute(text("""
                INSERT INTO sesiones (token_hash, usuario_id, vence_en)
                VALUES (:token_hash, :usuario_id, :vence_en)
            """), {
                "token_hash": token_hash,
                "usuario_id": usuario_id,
                "vence_en": vence_en,
            })

    def usuario_por_sesion(self, token_hash: str) -> dict | None:
        with get_engine().connect() as conexion:
            fila = conexion.execute(text("""
                SELECT u.id, u.correo, u.rol, u.perfil_id,
                       u.vigente_hasta, u.debe_cambiar_contrasena, p.grado
                FROM sesiones s
                JOIN usuarios u ON u.id = s.usuario_id
                LEFT JOIN perfiles_estudio p ON p.id = u.perfil_id
                WHERE s.token_hash = :token_hash
                  AND s.vence_en > CURRENT_TIMESTAMP
                  AND u.activo = 1
                  AND (u.vigente_hasta IS NULL OR u.vigente_hasta >= CURRENT_DATE)
            """), {"token_hash": token_hash}).mappings().first()
        return self._usuario(fila) if fila else None

    def cerrar_sesion(self, token_hash: str) -> None:
        with get_engine().begin() as conexion:
            conexion.execute(text("DELETE FROM sesiones WHERE token_hash = :token_hash"), {
                "token_hash": token_hash,
            })

    def cambiar_contrasena(self, usuario_id: str, contrasena_hash: str) -> None:
        with get_engine().begin() as conexion:
            conexion.execute(text("""
                UPDATE usuarios
                SET contrasena_hash = :hash, debe_cambiar_contrasena = 0
                WHERE id = :id
            """), {"hash": contrasena_hash, "id": usuario_id})

    def listar_cuentas(self) -> list[dict]:
        with get_engine().connect() as conexion:
            filas = conexion.execute(text("""
                SELECT u.id, u.correo, u.rol, u.vigente_hasta, u.activo, p.grado
                FROM usuarios u
                LEFT JOIN perfiles_estudio p ON p.id = u.perfil_id
                ORDER BY u.rol, u.correo
            """)).mappings().all()
        return [{
            "id": str(fila["id"]),
            "correo": fila["correo"],
            "rol": fila["rol"],
            "grado": int(fila["grado"]) if fila["grado"] is not None else None,
            "vigente_hasta": fila["vigente_hasta"].isoformat() if fila["vigente_hasta"] else None,
            "activo": bool(fila["activo"]),
        } for fila in filas]

    def desactivar(self, usuario_id: str) -> bool:
        with get_engine().begin() as conexion:
            resultado = conexion.execute(text("""
                UPDATE usuarios SET activo = 0 WHERE id = :id AND rol = 'alumno'
            """), {"id": usuario_id})
            conexion.execute(text("DELETE FROM sesiones WHERE usuario_id = :id"), {
                "id": usuario_id,
            })
        return bool(resultado.rowcount)

    def existe_directivo(self) -> bool:
        with get_engine().connect() as conexion:
            cantidad = conexion.execute(text("""
                SELECT COUNT(*) FROM usuarios WHERE rol = 'directivo'
            """)).scalar_one()
        return bool(cantidad)

    @staticmethod
    def _usuario(fila) -> dict:
        return {
            "id": str(fila["id"]),
            "correo": fila["correo"],
            "contrasena_hash": fila.get("contrasena_hash"),
            "rol": fila["rol"],
            "perfil_id": str(fila["perfil_id"]) if fila["perfil_id"] else None,
            "grado": int(fila["grado"]) if fila["grado"] is not None else None,
            "vigente_hasta": fila["vigente_hasta"].isoformat() if fila["vigente_hasta"] else None,
            "activo": bool(fila.get("activo", True)),
            "debe_cambiar_contrasena": bool(fila["debe_cambiar_contrasena"]),
        }
