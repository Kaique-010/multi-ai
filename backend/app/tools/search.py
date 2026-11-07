from langchain_community.tools import DuckDuckGoSearchRun
import logging



logger = logging.getLogger("multiagentes.search")


seach_tool = DuckDuckGoSearchRun()

async def realizar_buscas(query: str) -> str:
    """
    Realiza uma busca no DuckDuckGo e retorna o resultado.
    """
    try:
        logger.info(f"Buscando: {query}")
        return await seach_tool.ainvoke(query)

    except Exception as e:
        logger.error(f"Erro ao realizar busca: {e}")
        return f"Erro ao realizar busca: {e}"
