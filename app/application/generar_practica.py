"""Validación de ejercicios estructurados devueltos por el modelo local."""

from app.domain.errores_ia import IARespuestaInvalida


def validar_ejercicio(datos: dict) -> dict:
    if not isinstance(datos, dict):
        raise IARespuestaInvalida("La IA no devolvió un ejercicio válido.")

    enunciado = datos.get("enunciado")
    opciones = datos.get("opciones")
    respuesta = datos.get("respuesta_correcta")
    explicacion = datos.get("explicacion")

    if not isinstance(enunciado, str) or not enunciado.strip() or len(enunciado) > 1200:
        raise IARespuestaInvalida("El ejercicio generado no tiene una pregunta válida.")
    if not isinstance(opciones, list) or len(opciones) != 4:
        raise IARespuestaInvalida("El ejercicio debe incluir cuatro alternativas.")
    if any(not isinstance(opcion, str) or not opcion.strip() or len(opcion) > 500 for opcion in opciones):
        raise IARespuestaInvalida("Una alternativa del ejercicio no es válida.")
    limpias = [" ".join(opcion.split()).casefold() for opcion in opciones]
    if len(set(limpias)) != 4:
        raise IARespuestaInvalida("El ejercicio contiene alternativas repetidas.")
    if type(respuesta) is not int or not 0 <= respuesta < 4:
        raise IARespuestaInvalida("La IA no indicó una alternativa correcta válida.")
    if not isinstance(explicacion, str) or not explicacion.strip() or len(explicacion) > 2500:
        raise IARespuestaInvalida("El ejercicio no incluye una explicación utilizable.")

    return {
        "enunciado": enunciado.strip(),
        "opciones": [opcion.strip() for opcion in opciones],
        "respuesta_correcta": respuesta,
        "explicacion": explicacion.strip(),
    }
