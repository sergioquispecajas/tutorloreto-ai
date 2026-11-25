from app.domain.consulta import Consulta
from app.ports.consulta_repository import ConsultaRepository

def registrar_consulta(
    repo: ConsultaRepository,
    asignatura_id: int,
    pregunta: str,
    perfil_id: str | None = None,
) -> dict:
    consulta = Consulta(asignatura_id, pregunta.strip(), perfil_id)
    consulta.validar()
    return repo.registrar(consulta)
