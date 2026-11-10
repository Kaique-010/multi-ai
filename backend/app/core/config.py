from functools import lru_cache
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url
from langchain_community.embeddings import JinaEmbeddings

logger = logging.getLogger(__name__)


class Configuracoes(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    vector_db_name: str = "conhecimento"
    vector_db_user: str = "app"
    vector_db_password: str = ""
    vector_database_url: str = (
        "postgresql+asyncpg://app:app@banco-vetorial:5432/conhecimento"
    )

    # URL do banco de negócio (ERP remoto). Fonte única: MCP_POSTGRES_URL.
    mcp_postgres_url: str = ""

    cors_origins: str = "http://localhost:5173"
    cogne_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def origens_cors(self) -> list[str]:
        return [
            origem.strip()
            for origem in self.cors_origins.split(",")
            if origem.strip()
        ]

    @property
    def url_banco_negocio(self) -> str:
        """Normaliza MCP_POSTGRES_URL para o driver asyncpg do SQLAlchemy."""
        url = self.mcp_postgres_url.strip()

        if not url:
            raise ValueError("MCP_POSTGRES_URL não configurada.")

        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        parsed = make_url(url)

        if parsed.drivername not in ("postgresql", "postgresql+asyncpg"):
            raise ValueError("A URL deve apontar para PostgreSQL.")

        return parsed.set(drivername="postgresql+asyncpg").render_as_string(
            hide_password=False
        )


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()


configuracoes = obter_configuracoes()


def obter_provedor_embeddings() -> JinaEmbeddings:
    return JinaEmbeddings(
        jina_api_key=configuracoes.cogne_api_key,
        model_name="jina-embeddings-v3",
    )
