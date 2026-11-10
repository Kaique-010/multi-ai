import logging
import time
import uuid
from typing import Literal

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agents.state import EstadoAgente
from app.core.config import configuracoes
from app.core.observability import log_evento
from app.services.memorizer import memorizar_resposta
from app.services.retriever import buscar_contexto_com_score
from app.services.sql_service import (
    consultar_banco_negocio,
    listar_tabelas_negocio,
)
from app.tools.search import realizar_buscas

logger = logging.getLogger("multiagentes.graph")

# 1. Registro das ferramentas disponíveis para o modelo
ferramentas_disponiveis = [
    consultar_banco_negocio,
    listar_tabelas_negocio,
]

# 2. Inicialização do modelo e acoplamento das ferramentas via bind_tools
modelo_base = ChatOpenAI(
    model=configuracoes.deepseek_model,
    api_key=configuracoes.deepseek_api_key,
    base_url=configuracoes.deepseek_base_url.rstrip("/") + "/",
    temperature=0.2,
)

modelo_com_ferramentas = modelo_base.bind_tools(ferramentas_disponiveis)


# --- NÓS DO GRAFO ---

async def recuperar_contexto(estado: EstadoAgente) -> dict:
    """Consulta a memória vetorial (Jina v3 + PGVector) para checar similaridade."""
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="recuperar_contexto")

    try:
        contexto, score, encontrou_memoria = await buscar_contexto_com_score(
            estado["mensagem"],
            limite_distancia=0.28  # Threshold otimizado para evitar falsos positivos
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


def decidir_proximo_passo(
    estado: EstadoAgente,
) -> Literal["responder_com_memoria", "buscar_e_aprender"]:
    """Desvia o fluxo baseando-se no Hit/Miss da memória vetorial."""
    if estado.get("encontrou_memoria"):
        return "responder_com_memoria"
    return "buscar_e_aprender"


async def responder_com_memoria(estado: EstadoAgente) -> dict:
    """Responde diretamente a partir do conhecimento memorizado (Cache Hit)."""
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="responder_com_memoria")

    try:
        prompt_sistema = (
            "Você é um assistente de IA especialista em consultas ao banco de dados de negócio.\n"
            "Esta é uma conversa contínua: use o histórico acima para entender o contexto.\n"
            "Responda à pergunta do usuário em português brasileiro baseando-se no "
            f"conhecimento memorizado a seguir:\n\nContexto:\n{estado['contexto']}"
        )

        mensagens: list[BaseMessage] = [SystemMessage(content=prompt_sistema)]
        mensagens.extend(estado.get("historico", []))
        mensagens.append(HumanMessage(content=estado["mensagem"]))

        resultado = await modelo_base.ainvoke(mensagens)
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


async def _executar_tool_calls(
    mensagens: list[BaseMessage],
    ai_msg: AIMessage,
) -> list[BaseMessage]:
    """Executa tool_calls do modelo e anexa ToolMessage na sequência."""
    ferramentas_por_nome = {
        consultar_banco_negocio.name: consultar_banco_negocio,
        listar_tabelas_negocio.name: listar_tabelas_negocio,
    }

    for tool_call in ai_msg.tool_calls:
        nome = tool_call["name"]
        ferramenta = ferramentas_por_nome.get(nome)

        if ferramenta is None:
            mensagens.append(
                ToolMessage(
                    content=f"Ferramenta '{nome}' não disponível.",
                    tool_call_id=tool_call["id"],
                )
            )
            continue

        try:
            saida = await ferramenta.ainvoke(tool_call["args"])
        except Exception as erro:
            saida = f"Erro ao executar {nome}: {erro}"

        mensagens.append(
            ToolMessage(content=str(saida), tool_call_id=tool_call["id"])
        )

    return mensagens


async def buscar_e_aprender(estado: EstadoAgente) -> dict:
    """Executa buscas (Web + SQL Negócio via Tool Calling), responde e memoriza."""
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="buscar_e_aprender")

    try:
        historico = estado.get("historico", [])
        eh_follow_up = len(historico) > 0

        # 1. Busca web SÓ na primeira mensagem (follow-ups são sobre o mesmo tema)
        resultado_busca_web = ""
        if not eh_follow_up and len(estado["mensagem"].split()) >= 4:
            resultado_busca_web = await realizar_buscas(estado["mensagem"])

        # 2. Lista de tabelas só no primeiro turno; depois o modelo já conhece
        tabelas = ""
        if not eh_follow_up:
            tabelas = await listar_tabelas_negocio.ainvoke({})

        prompt_sistema = (
            "Você é um assistente de IA especialista em consultas ao banco de dados de negócio.\n"
            "Esta é uma conversa contínua: use o histórico acima para entender o contexto "
            "e NÃO repita explicações já dadas.\n\n"
        )

        if tabelas:
            prompt_sistema += (
                f"Tabelas disponíveis no banco de negócio:\n{tabelas}\n\n"
            )

        if resultado_busca_web:
            prompt_sistema += (
                f"Resultados da busca web (use apenas se relevante):\n{resultado_busca_web}\n\n"
            )

        prompt_sistema += (
            "Instruções:\n"
            "- Se precisar de dados do banco, CHAME a ferramenta `consultar_banco_negocio` "
            "com um SELECT (não descreva, execute).\n"
            "- Em follow-ups, continue de onde parou sem re-listar estrutura.\n"
            "- Responda em português brasileiro de forma objetiva."
        )

        mensagens: list[BaseMessage] = [SystemMessage(content=prompt_sistema)]
        mensagens.extend(historico)
        mensagens.append(HumanMessage(content=estado["mensagem"]))

        # 3. Loop de tool calling: executa até o modelo parar de chamar ferramentas
        max_iteracoes = 5
        for _ in range(max_iteracoes):
            resultado_llm = await modelo_com_ferramentas.ainvoke(mensagens)
            mensagens.append(resultado_llm)

            if not resultado_llm.tool_calls:
                break

            mensagens = await _executar_tool_calls(mensagens, resultado_llm)

        resposta_final = str(resultado_llm.content)

        # 4. APRENDE: Salva o novo conhecimento no PGVector via Jina v3
        await memorizar_resposta(estado["mensagem"], resposta_final)

        log_evento(
            logger,
            logging.INFO,
            "node.completed",
            node="buscar_e_aprender",
            duration_ms=round((time.perf_counter() - inicio) * 1000, 2),
        )

        return {"resposta": resposta_final}

    except Exception:
        logger.exception(
            "node.failed",
            extra={"event": "node.failed", "node": "buscar_e_aprender"},
        )
        raise


# --- MONTAGEM DO GRAFO ---
construtor = StateGraph(EstadoAgente)

construtor.add_node("recuperar_contexto", recuperar_contexto)
construtor.add_node("responder_com_memoria", responder_com_memoria)
construtor.add_node("buscar_e_aprender", buscar_e_aprender)

construtor.add_edge(START, "recuperar_contexto")

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


# --- EXECUÇÃO PELO FASTAPI ---
async def executar_grafo(
    mensagem: str,
    historico: list[BaseMessage] | None = None,
) -> str:
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
                "historico": historico or [],
                "contexto": "",
                "score": 0.0,
                "encontrou_memoria": False,
                "resposta": "",
                "mensagens": [],
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