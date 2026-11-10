from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from app.api.schemas import MensagemChat, RespostaChat
from app.agents.graph import executar_grafo

# Removemos o prefixo do APIRouter e definimos a rota completa ou deixamos sem a barra final
router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=RespostaChat)  # <- Mudei de "/" para ""
@router.post("/", response_model=RespostaChat) # <- Garante ambos os caminhos
async def conversar(dados: MensagemChat) -> RespostaChat:
    try:
        historico = [
            HumanMessage(content=m.content)
            if m.role == "user"
            else AIMessage(content=m.content)
            for m in dados.historico
        ]

        resposta = await executar_grafo(dados.mensagem, historico=historico)
        return RespostaChat(resposta=resposta)

    except ValueError as erro:
        raise HTTPException(
            status_code=500,
            detail=str(erro),
        ) from erro

    except Exception as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter uma resposta do modelo de IA.",
        ) from erro