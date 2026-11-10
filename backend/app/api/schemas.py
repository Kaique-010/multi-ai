from typing import Literal

from pydantic import BaseModel, Field


class MensagemHistorico(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class MensagemChat(BaseModel):
    mensagem: str = Field(
        min_length=1,
        max_length=10000,
        description="Mensagem enviada pelo usuário",
    )
    historico: list[MensagemHistorico] = Field(
        default_factory=list,
        description="Histórico da conversa (mais antigo primeiro).",
    )


class RespostaChat(BaseModel):
    resposta: str = Field(
        min_length=1,
        max_length=10000,
        description="Resposta do modelo de IA",
    )
