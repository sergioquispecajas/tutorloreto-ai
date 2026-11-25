"""Persistencia MySQL para el perfil anónimo y las actividades de aprendizaje."""

import json

from sqlalchemy import text

from app.infrastructure.database import get_engine


def _fecha(valor):
    return valor.isoformat() if valor is not None else None


class MySQLAprendizajeRepository:
    def guardar_perfil(self, perfil_id: str, grado: int) -> dict:
        with get_engine().begin() as conexion:
            conexion.execute(
                text("""
                    INSERT INTO perfiles_estudio (id, grado)
                    VALUES (:id, :grado)
                    ON DUPLICATE KEY UPDATE
                        grado = :grado,
                        actualizado_en = CURRENT_TIMESTAMP
                """),
                {"id": perfil_id, "grado": grado},
            )
            fila = conexion.execute(
                text("""
                    SELECT id, grado, creado_en, actualizado_en
                    FROM perfiles_estudio WHERE id = :id
                """),
                {"id": perfil_id},
            ).mappings().one()
        return {
            "perfil_id": fila["id"],
            "grado": int(fila["grado"]),
            "creado_en": _fecha(fila["creado_en"]),
            "actualizado_en": _fecha(fila["actualizado_en"]),
        }

    def obtener_perfil(self, perfil_id: str) -> dict | None:
        with get_engine().connect() as conexion:
            fila = conexion.execute(
                text("""
                    SELECT id, grado, creado_en, actualizado_en
                    FROM perfiles_estudio WHERE id = :id
                """),
                {"id": perfil_id},
            ).mappings().first()
        if fila is None:
            return None
        return {
            "perfil_id": fila["id"],
            "grado": int(fila["grado"]),
            "creado_en": _fecha(fila["creado_en"]),
            "actualizado_en": _fecha(fila["actualizado_en"]),
        }

    def guardar_practica(self, datos: dict) -> int:
        with get_engine().begin() as conexion:
            parametros = {
                "perfil_id": datos["perfil_id"],
                "asignatura_id": datos["asignatura_id"],
                "tema": datos["tema"],
                "dificultad": datos["dificultad"],
                "enunciado": datos["enunciado"],
                "opciones_json": json.dumps(datos["opciones"], ensure_ascii=False),
                "respuesta_correcta": datos["respuesta_correcta"],
                "explicacion": datos["explicacion"],
            }
            resultado = conexion.execute(
                text("""
                    INSERT INTO practicas (
                        perfil_id, asignatura_id, tema, dificultad, enunciado,
                        opciones_json, respuesta_correcta, explicacion
                    ) VALUES (
                        :perfil_id, :asignatura_id, :tema, :dificultad, :enunciado,
                        :opciones_json, :respuesta_correcta, :explicacion
                    )
                """),
                parametros,
            )
            return int(resultado.lastrowid)

    def obtener_practica(self, practica_id: int, perfil_id: str) -> dict | None:
        with get_engine().connect() as conexion:
            fila = conexion.execute(
                text("""
                    SELECT id, perfil_id, asignatura_id, tema, dificultad,
                           enunciado, opciones_json, respuesta_correcta,
                           explicacion, respuesta_elegida, correcta, creado_en,
                           respondido_en
                    FROM practicas
                    WHERE id = :id AND perfil_id = :perfil_id
                """),
                {"id": practica_id, "perfil_id": perfil_id},
            ).mappings().first()
        if fila is None:
            return None
        return self._practica(fila)

    def responder_practica(
        self, practica_id: int, perfil_id: str, opcion: int
    ) -> dict | None:
        with get_engine().begin() as conexion:
            fila = conexion.execute(
                text("""
                    SELECT id, respuesta_correcta, explicacion,
                           respuesta_elegida, correcta
                    FROM practicas
                    WHERE id = :id AND perfil_id = :perfil_id
                    FOR UPDATE
                """),
                {"id": practica_id, "perfil_id": perfil_id},
            ).mappings().first()
            if fila is None:
                return None

            repetida = fila["respuesta_elegida"] is not None
            elegida = (
                int(fila["respuesta_elegida"]) if repetida else opcion
            )
            correcta = (
                bool(fila["correcta"])
                if repetida
                else elegida == int(fila["respuesta_correcta"])
            )
            if not repetida:
                conexion.execute(
                    text("""
                        UPDATE practicas
                        SET respuesta_elegida = :opcion,
                            correcta = :correcta,
                            respondido_en = CURRENT_TIMESTAMP
                        WHERE id = :id AND perfil_id = :perfil_id
                    """),
                    {
                        "id": practica_id,
                        "perfil_id": perfil_id,
                        "opcion": elegida,
                        "correcta": correcta,
                    },
                )
            return {
                "practica_id": practica_id,
                "opcion_elegida": elegida,
                "opcion_correcta": int(fila["respuesta_correcta"]),
                "correcta": correcta,
                "explicacion": fila["explicacion"],
                "repetida": repetida,
            }

    def historial(self, perfil_id: str, limite: int = 50) -> list[dict]:
        limite = max(1, min(int(limite), 100))
        with get_engine().connect() as conexion:
            consultas = conexion.execute(
                text("""
                    SELECT c.id, c.asignatura_id, a.nombre AS asignatura,
                           c.pregunta, c.estado, c.creado_en,
                           (SELECT r.contenido FROM respuestas r
                            WHERE r.consulta_id = c.id
                            ORDER BY r.id DESC LIMIT 1) AS explicacion
                    FROM consultas c
                    JOIN asignaturas a ON a.id = c.asignatura_id
                    WHERE c.perfil_id = :perfil_id
                    ORDER BY c.creado_en DESC, c.id DESC
                    LIMIT :limite
                """),
                {"perfil_id": perfil_id, "limite": limite},
            ).mappings().all()
            practicas = conexion.execute(
                text("""
                    SELECT p.id, p.asignatura_id, a.nombre AS asignatura,
                           p.tema, p.dificultad, p.enunciado, p.opciones_json,
                           p.respuesta_correcta, p.correcta, p.respuesta_elegida,
                           p.explicacion, p.creado_en, p.respondido_en
                    FROM practicas p
                    JOIN asignaturas a ON a.id = p.asignatura_id
                    WHERE p.perfil_id = :perfil_id
                    ORDER BY p.creado_en DESC, p.id DESC
                    LIMIT :limite
                """),
                {"perfil_id": perfil_id, "limite": limite},
            ).mappings().all()

        actividades = []
        for fila in consultas:
            actividades.append({
                "tipo": "consulta",
                "id": int(fila["id"]),
                "asignatura_id": int(fila["asignatura_id"]),
                "asignatura": fila["asignatura"],
                "tema": None,
                "detalle": fila["pregunta"],
                "estado": fila["estado"],
                "correcta": None,
                "explicacion": fila["explicacion"],
                "creado_en": _fecha(fila["creado_en"]),
            })
        for fila in practicas:
            opciones = fila["opciones_json"]
            if isinstance(opciones, str):
                opciones = json.loads(opciones)
            estado = "PENDIENTE"
            if fila["respuesta_elegida"] is not None:
                estado = "ACIERTO" if fila["correcta"] else "PARA_REFORZAR"
            actividades.append({
                "tipo": "practica",
                "id": int(fila["id"]),
                "asignatura_id": int(fila["asignatura_id"]),
                "asignatura": fila["asignatura"],
                "tema": fila["tema"],
                "dificultad": fila["dificultad"],
                "detalle": fila["enunciado"],
                "estado": estado,
                "respuesta_elegida": (
                    opciones[int(fila["respuesta_elegida"])]
                    if fila["respuesta_elegida"] is not None
                    else None
                ),
                "respuesta_correcta": (
                    opciones[int(fila["respuesta_correcta"])]
                    if fila["respuesta_elegida"] is not None
                    else None
                ),
                "explicacion": (
                    fila["explicacion"]
                    if fila["respuesta_elegida"] is not None
                    else None
                ),
                "correcta": (
                    bool(fila["correcta"])
                    if fila["correcta"] is not None
                    else None
                ),
                "creado_en": _fecha(fila["creado_en"]),
            })
        actividades.sort(
            key=lambda item: (item["creado_en"] or "", item["id"]),
            reverse=True,
        )
        return actividades[:limite]

    def progreso(self, perfil_id: str) -> dict:
        with get_engine().connect() as conexion:
            grupos = conexion.execute(
                text("""
                    SELECT p.asignatura_id, a.nombre AS asignatura, p.tema,
                           COUNT(*) AS intentos,
                           SUM(CASE WHEN p.correcta = 1 THEN 1 ELSE 0 END) AS aciertos,
                           ROUND(
                               100 * SUM(CASE WHEN p.correcta = 1 THEN 1 ELSE 0 END)
                               / COUNT(*), 1
                           ) AS porcentaje_aciertos
                    FROM practicas p
                    JOIN asignaturas a ON a.id = p.asignatura_id
                    WHERE p.perfil_id = :perfil_id
                      AND p.respuesta_elegida IS NOT NULL
                    GROUP BY p.asignatura_id, a.nombre, p.tema
                    ORDER BY porcentaje_aciertos ASC, intentos DESC, p.tema ASC
                """),
                {"perfil_id": perfil_id},
            ).mappings().all()
            total_consultas = conexion.execute(
                text("""
                    SELECT COUNT(*) FROM consultas WHERE perfil_id = :perfil_id
                """),
                {"perfil_id": perfil_id},
            ).scalar_one()

        temas = []
        for fila in grupos:
            porcentaje = float(fila["porcentaje_aciertos"] or 0)
            temas.append({
                "asignatura_id": int(fila["asignatura_id"]),
                "asignatura": fila["asignatura"],
                "tema": fila["tema"],
                "intentos": int(fila["intentos"]),
                "aciertos": int(fila["aciertos"] or 0),
                "porcentaje_aciertos": porcentaje,
            })
        total_practicas = sum(item["intentos"] for item in temas)
        aciertos = sum(item["aciertos"] for item in temas)
        return {
            "total_consultas": int(total_consultas),
            "total_practicas": total_practicas,
            "aciertos": aciertos,
            "porcentaje_aciertos": (
                round(100 * aciertos / total_practicas, 1)
                if total_practicas
                else 0.0
            ),
            "temas": temas,
        }

    @staticmethod
    def _practica(fila) -> dict:
        opciones = fila["opciones_json"]
        if isinstance(opciones, str):
            opciones = json.loads(opciones)
        return {
            "id": int(fila["id"]),
            "perfil_id": fila["perfil_id"],
            "asignatura_id": int(fila["asignatura_id"]),
            "tema": fila["tema"],
            "dificultad": fila["dificultad"],
            "enunciado": fila["enunciado"],
            "opciones": opciones,
            "respuesta_correcta": int(fila["respuesta_correcta"]),
            "explicacion": fila["explicacion"],
            "respuesta_elegida": (
                int(fila["respuesta_elegida"])
                if fila["respuesta_elegida"] is not None
                else None
            ),
            "correcta": (
                bool(fila["correcta"]) if fila["correcta"] is not None else None
            ),
            "creado_en": _fecha(fila["creado_en"]),
            "respondido_en": _fecha(fila["respondido_en"]),
        }
