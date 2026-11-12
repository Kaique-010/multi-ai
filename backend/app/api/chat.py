from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from app.api.schemas import MensagemChat, RespostaChat
from app.services.memory_service import obter_historico_do_apredizado
from app.agents.graph import executar_grafo

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=RespostaChat)
@router.post("/", response_model=RespostaChat)
async def conversar(dados: MensagemChat) -> RespostaChat:
    try:
        # Monta apenas o histórico recente da janela de chat do usuário
        historico_mensagens = [
            HumanMessage(content=m.content)
            if m.role == "user"
            else AIMessage(content=m.content)
            for m in dados.historico
        ]

        resposta = await executar_grafo(dados.mensagem, historico=historico_mensagens)
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


@router.get("/historico")
async def buscar_historico():
    """Retorna as perguntas/memórias acumuladas no PGVector."""
    historico = await obter_historico_do_apredizado()
    return {"historico": historico}