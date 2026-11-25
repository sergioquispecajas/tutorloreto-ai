"""Inicializa el esquema MySQL de una instalación alojada en la nube.

El script usa solo CREATE TABLE IF NOT EXISTS e INSERT IGNORE del archivo
schema_hosted.sql, por lo que se puede volver a ejecutar sin borrar registros.
"""

from pathlib import Path

from app.infrastructure.database import get_engine


def inicializar_esquema() -> int:
    archivo = Path(__file__).resolve().parents[2] / "sql" / "schema_hosted.sql"
    contenido = archivo.read_text(encoding="utf-8-sig")
    # Quita comentarios completos antes de separar sentencias: un punto y coma
    # dentro de un comentario no debe convertirse en un separador SQL.
    contenido_sql = "\n".join(
        linea
        for linea in contenido.splitlines()
        if not linea.lstrip().startswith("--")
    )
    sentencias = [
        sentencia.strip()
        for sentencia in contenido_sql.split(";")
        if sentencia.strip()
    ]

    engine = get_engine()
    with engine.begin() as conexion:
        for sentencia in sentencias:
            conexion.exec_driver_sql(sentencia)
    return len(sentencias)


if __name__ == "__main__":
    total = inicializar_esquema()
    print(f"Esquema TutorLoreto AI listo: {total} sentencias aplicadas.")
