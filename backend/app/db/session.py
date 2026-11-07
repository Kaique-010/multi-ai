
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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


async def verificar_banco_vetorial() -> bool:
    async with motor.connect() as conexao:
        await conexao.execute(text("SELECT 1"))

    return True
