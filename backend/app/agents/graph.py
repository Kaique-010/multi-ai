import logging
import time
import uuid
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agents.state import EstadoAgente
from app.core.config import configuracoes
from app.core.observability import log_evento
from app.services.memorizer import memorizar_resposta
from app.services.retriever import buscar_contexto_com_score
from app.mcp.mcp_client import obter_ferramentas_mcp
from app.tools.search import realizar_buscas

logger = logging.getLogger("multiagentes.graph")

modelo_base = ChatOpenAI(
    model=configuracoes.deepseek_model,
    api_key=configuracoes.deepseek_api_key,
    base_url=configuracoes.deepseek_base_url.rstrip("/") + "/",
    temperature=0.1,  # Temperatura mais baixa para garantir precisão técnica em queries
)

async def recuperar_contexto(estado: EstadoAgente) -> dict:
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="recuperar_contexto")

    try:
        contexto, score, encontrou_memoria = await buscar_contexto_com_score(
            estado["mensagem"],
            limite_distancia=0.20  # Threshold rigoroso
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
        logger.exception("node.failed", extra={"event": "node.failed", "node": "recuperar_contexto"})
        raise

def decidir_proximo_passo(estado: EstadoAgente) -> Literal["responder_com_memoria", "buscar_e_aprender"]:
    if estado.get("encontrou_memoria"):
        return "responder_com_memoria"
    return "buscar_e_aprender"

async def responder_com_memoria(estado: EstadoAgente) -> dict:
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="responder_com_memoria")

    try:
        prompt_sistema = (
            "Você é um assistente especialista de IA.\n"
            "Responda à pergunta do usuário em português brasileiro baseando-se no "
            f"conhecimento memorizado a seguir:\n\nContexto:\n{estado['contexto']}"
        )

        mensagens: list[BaseMessage] = [SystemMessage(content=prompt_sistema)]
        mensagens.extend(estado.get("historico", []))
        mensagens.append(HumanMessage(content=estado["mensagem"]))

        resultado = await modelo_base.ainvoke(mensagens)
        return {"resposta": str(resultado.content)}
    except Exception:
        logger.exception("node.failed", extra={"event": "node.failed", "node": "responder_com_memoria"})
        raise

async def buscar_e_aprender(estado: EstadoAgente) -> dict:
    """Usa o protocolo MCP do PostgreSQL com ReAct loop (while) até a conclusão."""
    inicio = time.perf_counter()
    log_evento(logger, logging.INFO, "node.started", node="buscar_e_aprender")

    try:
        # 1. Carrega as ferramentas dinâmicas via MCP Server (SaveWeb ERP)
        ferramentas_mcp = await obter_ferramentas_mcp()
        modelo_com_mcp = modelo_base.bind_tools(ferramentas_mcp) if ferramentas_mcp else modelo_base

        # 2. Avalia a intenção da mensagem
        prompt_classificador = (
            "Análise a intenção do usuário:\n"
            "Se for sobre dados internos de banco de dados (pedidos, vendas, clientes, estoque, tabelas), "
            "responda apenas 'BANCO'. Se for sobre assuntos externos ou conhecimento geral, responda apenas 'WEB'."
        )
        
        decisao = await modelo_base.ainvoke([
            SystemMessage(content=prompt_classificador),
            HumanMessage(content=estado["mensagem"])
        ])

        intencao = str(decisao.content).strip().upper()

        if "BANCO" in intencao and ferramentas_mcp:
            # System Prompt instruindo o modelo a ser autônomo e concluir a consulta sem pedir permissão
            prompt_mcp = (
                "Você é um especialista em PostgreSQL atuando sobre o banco do ERP SaveWeb via protocolo MCP.\n"
                "Instruções:\n"
                "1. Inspecione as tabelas/estruturas necessárias usando as ferramentas MCP.\n"
                "2. Monte e execute a query SQL de leitura com os totalizadores/contagens solicitados.\n"
                "3. NÃO pare para pedir confirmação do usuário entre os passos; execute as ferramentas até obter a resposta final.\n"
                "4. Responda em português brasileiro com os valores exatos calculados."
            )

            mensagens: list[BaseMessage] = [SystemMessage(content=prompt_mcp)]
            mensagens.extend(estado.get("historico", []))
            mensagens.append(HumanMessage(content=estado["mensagem"]))

            # --- LOOP AUTÔNOMO (WHILE) ---
            max_iteracoes = 5
            iteracao = 0

            while iteracao < max_iteracoes:
                iteracao += 1
                resposta_llm = await modelo_com_mcp.ainvoke(mensagens)
                mensagens.append(resposta_llm)

                # Se o modelo NÃO pediu mais nenhuma ferramenta, significa que ele concluiu e deu a resposta final!
                if not resposta_llm.tool_calls:
                    resposta = str(resposta_llm.content)
                    break

                # Caso o modelo tenha pedido a execução de ferramentas:
                for tc in resposta_llm.tool_calls:
                    log_evento(
                        logger, 
                        logging.INFO, 
                        f"Iteração {iteracao}: Executando Tool MCP {tc['name']}", 
                        tool_args=tc['args']
                    )

                    tool_obj = next((t for t in ferramentas_mcp if t.name == tc["name"]), None)
                    if tool_obj:
                        res_tool = await tool_obj.ainvoke(tc["args"])
                    else:
                        res_tool = f"Ferramenta {tc['name']} não encontrada."

                    # Adiciona a resposta da ferramenta na sequência de mensagens para o próximo ciclo do while
                    mensagens.append(ToolMessage(content=str(res_tool), tool_call_id=tc["id"]))

            else:
                # Caso atinja o limite máximo de iterações do loop
                resposta = str(resposta_llm.content)

        else:
            # Caminho Web clássico
            resultado_web = await realizar_buscas(estado["mensagem"])
            prompt_web = (
                "Responda com clareza em português brasileiro com base nas informações abaixo:\n\n"
                f"Resultados Web:\n{resultado_web}"
            )
            resposta_llm = await modelo_base.ainvoke([
                SystemMessage(content=prompt_web),
                HumanMessage(content=estado["mensagem"])
            ])
            resposta = str(resposta_llm.content)

        # 3. Memoriza o resultado final no PGVector
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
        logger.exception("node.failed", extra={"event": "node.failed", "node": "buscar_e_aprender"})
        raise
# --- Grafo ---
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

async def executar_grafo(mensagem: str, historico: list[BaseMessage] | None = None) -> str:
    graph_run_id = str(uuid.uuid4())
    inicio = time.perf_counter()

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
            config={"metadata": {"graph_run_id": graph_run_id}},
        )
        return resultado["resposta"]
    except Exception:
        logger.exception("graph.failed", extra={"graph_run_id": graph_run_id})
        raise