from pydantic import BaseModel, Field


class MensagemChat(BaseModel):
    mensagem: str = Field(
        min_length=1,
        max_length=10000,
        description="Mensagem enviada pelo usuário",
    )


class RespostaChat(BaseModel):
    resposta: str = Field(
        min_length=1,
        max_length=10000,
        description="Resposta do modelo de IA",
    )