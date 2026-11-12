import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from app.core.config import configuracoes

logger = logging.getLogger("multiagentes.mcp")

_mcp_client = None

async def obter_ferramentas_mcp():
    """Conecta o MCP exclusivamente ao PostgreSQL do ERP (SaveWeb)."""
    global _mcp_client

    # Força o uso da URL do ERP de negócio (saveweb001)
    url_mcp = configuracoes.mcp_postgres_url.strip()

    if not url_mcp:
        logger.error("MCP_POSTGRES_URL não está configurada no .env!")
        return []

    try:
        if _mcp_client is None:
            logger.info(f"Conectando servidor MCP PostgreSQL no ERP de negócio...")
            _mcp_client = MultiServerMCPClient({
                "postgres": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-postgres",
                        url_mcp
                    ],
                    "transport": "stdio",
                }
            })

        ferramentas = await _mcp_client.get_tools()
        logger.info(f"MCP conectado ao ERP SaveWeb com sucesso! Ferramentas: {[f.name for f in ferramentas]}")
        return ferramentas

    except Exception as e:
        logger.error(f"Erro ao conectar o MCP ao banco do ERP: {e}")
        return []