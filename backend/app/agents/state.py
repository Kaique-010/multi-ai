from typing import TypedDict

from langchain_core.messages import BaseMessage


class EstadoAgente(TypedDict):
    mensagem: str
    historico: list[BaseMessage]
    contexto: str
    score: float
    encontrou_memoria: bool
    resposta: str
    mensagens: list[BaseMessage]
