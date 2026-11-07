from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import configuracoes

motor = create_async_engine(
    configuracoes.vector_database_url,
    pool_pre_ping=True,
)

SessaoBanco = async_sessionmaker(
    bind=motor,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def inicializar_banco_vetorial() -> None:
    """Garante que a extensão pgvector e a tabela de embeddings existam."""
    async with motor.begin() as conexao:
        await conexao.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conexao.execute(text("""
            CREATE TABLE IF NOT EXISTS documentos_conhecimento (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conteudo TEXT NOT NULL,
                metadata_json JSONB DEFAULT '{}'::jsonb,
                embedding vector(1024)
            );
        """))