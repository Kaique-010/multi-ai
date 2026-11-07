from typing import TypedDict

class EstadoAgente(TypedDict):
    mensagem: str
    contexto: str
    encontrou_memoria: bool
    resposta: str