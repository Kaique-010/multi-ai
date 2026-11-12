import logging
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

logger = logging.getLogger("multiagentes.search")

async def realizar_buscas(query: str) -> str:
    """Executa buscas web de forma resiliente e sem expor erros de DNS no prompt."""
    try:
        logger.info(f"Buscando na Web: {query}")
        
        # Instancia o wrapper limitando os resultados e tempo
        wrapper = DuckDuckGoSearchAPIWrapper(region="pt-br", time="y", max_results=5)
        search_tool = DuckDuckGoSearchRun(api_wrapper=wrapper)
        
        resultado = await search_tool.ainvoke(query)
        return str(resultado)

    except Exception as e:
        logger.warning(f"Aviso na busca web ({type(e).__name__}): {e}")
        # Em vez de retornar a string de erro do Python, retorna uma resposta neutra 
        # para a LLM responder com a própria base de conhecimento sem justificativas de DNS.
        return "Busca web temporariamente indisponível. Responda com base no seu conhecimento de sistema."