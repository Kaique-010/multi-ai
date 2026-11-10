from functools import lru_cache
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
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


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()


configuracoes = obter_configuracoes()


def obter_provedor_embeddings() -> JinaEmbeddings:
    return JinaEmbeddings(
        jina_api_key=configuracoes.cogne_api_key,
        model_name="jina-embeddings-v3",  # Nome correto do modelo
    )


origens_cors = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8001",
]