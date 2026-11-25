"""Puerto de salida: abstracción del generador de explicaciones académicas."""
from typing import Protocol


class GeneradorExplicaciones(Protocol):
    def generar(
        self,
        *,
        pregunta: str,
        asignatura: str,
        grado: int | None = None,
    ) -> str:
        """Retorna una explicación pedagógica generada localmente."""
        ...

    def generar_ejercicio(
        self,
        *,
        tema: str,
        asignatura: str,
        grado: int,
        dificultad: str,
    ) -> dict:
        """Genera un ejercicio adaptado al grado y nivel solicitado."""
        ...

    def analizar_progreso(
        self,
        *,
        grado: int,
        progreso: dict,
        historial: list[dict],
    ) -> str:
        """Resume el historial y propone refuerzo basado en actividad real."""
        ...
