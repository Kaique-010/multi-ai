import logging
import time
import uuid
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agents.state import EstadoAgente
from app.core.config import configuracoes
from app.core.observability import log_evento
from app.services.memorizer import memorizar_resposta
from app.services.retriever import buscar_contexto_com_score
from app.tools.search import realizar_buscas

logger = logging.getLogger("multiagentes.graph")

modelo = ChatOpenAI(
    model=configuracoes.deepseek_model,
    api_key=configuracoes.deepseek_api_key,
    base_url=configuracoes.deepseek_base_url.rstrip("/") + "/",
    temperature=0.2,
)


# 1. Nó Inicial: Consulta a Memória Vetorial
async def recuperar_contexto(estado: EstadoAgente) -> dict:
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="recuperar_contexto")

    try:
        contexto, score, encontrou_memoria = await buscar_contexto_com_score(
            estado["mensagem"]
        )

        log_evento(
            logger,
            logging.INFO,
            "node.completed",
            node="recuperar_contexto",
            encontrou_memoria=encontrou_memoria,
            score=score,
            duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
        )

        return {
            "contexto": contexto,
            "score": score,
            "encontrou_memoria": encontrou_memoria,
        }
    except Exception:
        logger.exception(
            "node.failed",
            extra={"event": "node.failed", "node": "recuperar_contexto"},
        )
        raise


# 2. Decisor de Rota (Edge Condicional)
def decidir_proximo_passo(
    estado: EstadoAgente,
) -> Literal["responder_com_memoria", "buscar_e_aprender"]:
    if estado.get("encontrou_memoria"):
        return "responder_com_memoria"
    return "buscar_e_aprender"


# 3A. Nó de Resposta Direta da Memória (Hit de Cache)
async def responder_com_memoria(estado: EstadoAgente) -> dict:
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="responder_com_memoria")

    try:
        prompt_sistema = (
            "Você é um assistente de IA especialista.\n"
            "Responda à pergunta do usuário em português brasileiro baseando-se no "
            f"conhecimento memorizado a seguir:\n\nContexto:\n{estado['contexto']}"
        )

        mensagens = [
            SystemMessage(content=prompt_sistema),
            HumanMessage(content=estado["mensagem"]),
        ]

        resultado = await modelo.ainvoke(mensagens)
        resposta = str(resultado.content)

        log_evento(
            logger,
            logging.INFO,
            "node.completed",
            node="responder_com_memoria",
            duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
        )

        return {"resposta": resposta}

    except Exception:
        logger.exception(
            "node.failed",
            extra={"event": "node.failed", "node": "responder_com_memoria"},
        )
        raise


# 3B. Nó de Busca Externa + Síntese + Aprendizado Automático (Miss de Cache)
async def buscar_e_aprender(estado: EstadoAgente) -> dict:
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="buscar_e_aprender")

    try:
        # 1. Executa a Tool de busca web
        resultado_busca = await realizar_buscas(estado["mensagem"])

        # 2. Gera a resposta via DeepSeek com os dados frescos
        prompt_sistema = (
            "Você é um assistente de IA especialista.\n"
            "Responda à pergunta do usuário em português brasileiro com base nos "
            f"resultados atualizados obtidos da busca a seguir:\n\nResultados:\n{resultado_busca}"
        )

        mensagens = [
            SystemMessage(content=prompt_sistema),
            HumanMessage(content=estado["mensagem"]),
        ]

        resultado_llm = await modelo.ainvoke(mensagens)
        resposta = str(resultado_llm.content)

        # 3. APRENDE: Grava o par pergunta + resposta no PGVector usando Jina AI v3
        await memorizar_resposta(estado["mensagem"], resposta)

        log_evento(
            logger,
            logging.INFO,
            "node.completed",
            node="buscar_e_aprender",
            duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
        )

        return {"resposta": resposta}

    except Exception:
        logger.exception(
            "node.failed",
            extra={"event": "node.failed", "node": "buscar_e_aprender"},
        )
        raise


# --- Montagem do Grafo ---
construtor = StateGraph(EstadoAgente)

# Nós
construtor.add_node("recuperar_contexto", recuperar_contexto)
construtor.add_node("responder_com_memoria", responder_com_memoria)
construtor.add_node("buscar_e_aprender", buscar_e_aprender)

# Fluxo de execução
construtor.add_edge(START, "recuperar_contexto")

# Roteamento Condicional
construtor.add_conditional_edges(
    "recuperar_contexto",
    decidir_proximo_passo,
    {
        "responder_com_memoria": "responder_com_memoria",
        "buscar_e_aprender": "buscar_e_aprender",
    },
)

construtor.add_edge("responder_com_memoria", END)
construtor.add_edge("buscar_e_aprender", END)

grafo = construtor.compile()


# --- Invocação Externa pelo FastAPI ---
async def executar_grafo(mensagem: str) -> str:
    graph_run_id = str(uuid.uuid4())
    inicio = time.perf_counter()

    log_evento(
        logger,
        logging.INFO,
        "state.received",
        graph_run_id=graph_run_id,
        state_name="EstadoAgente",
    )

    log_evento(
        logger,
        logging.INFO,
        "graph.started",
        graph_run_id=graph_run_id,
    )

    try:
        resultado = await grafo.ainvoke(
            {
                "mensagem": mensagem,
                "contexto": "",
                "score": 0.0,
                "encontrou_memoria": False,
                "resposta": "",
            },
            config={
                "metadata": {
                    "graph_run_id": graph_run_id,
                }
            },
        )

        log_evento(
            logger,
            logging.INFO,
            "state.updated",
            graph_run_id=graph_run_id,
            state_name="EstadoAgente",
            fields_updated=["resposta"],
        )

        log_evento(
            logger,
            logging.INFO,
            "graph.completed",
            graph_run_id=graph_run_id,
            duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
        )

        return resultado["resposta"]

    except Exception:
        logger.exception(
            "graph.failed",
            extra={
                "event": "graph.failed",
                "graph_run_id": graph_run_id,
                "duration_ms": round((time.perf_counter() - inicio) * 1000, 2),
            },
        )
        raise