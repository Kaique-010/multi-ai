
import re

from langchain_core.tools import tool
from sqlalchemy import text

from app.core.config import configuracoes
from app.db.session import motor_negocio


@tool
async def listar_tabelas_negocio() -> str:
    """Lista as tabelas e views acessíveis no schema public do banco de negócio.
    Use antes de consultar dados quando não conhecer a estrutura do banco."""
    sql = text("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        LIMIT 200
    """)

    async with motor_negocio.connect() as conexao:
        async with conexao.begin():
            await conexao.exec_driver_sql(
                "SET TRANSACTION READ ONLY"
            )
            resultado = await conexao.execute(sql)
            linhas = resultado.mappings().all()

    if not linhas:
        return "Nenhuma tabela encontrada no schema public."

    return "\n".join(
        f"{linha['table_name']} ({linha['table_type']})"
        for linha in linhas
    )


@tool
async def consultar_banco_negocio(sql: str) -> str:
    """Executa consultas SQL somente de leitura no PostgreSQL de negócio.
    Use para perguntas sobre dados internos. Consulte primeiro
    listar_tabelas_negocio se não conhecer as tabelas.
    Aceita SELECT e WITH somente para leitura. Limita a 100 registros.
    Não use para pesquisas na internet."""

    consulta = sql.strip().rstrip(";").strip()

    if not consulta:
        return "Consulta SQL vazia."

    # Aceita apenas uma consulta iniciada por SELECT ou WITH.
    if not re.match(r"^(SELECT|WITH)\b", consulta, re.IGNORECASE):
        return "Consulta bloqueada: somente SELECT ou WITH são permitidos."

    # Bloqueia comandos de escrita e comandos administrativos.
    proibidos = re.compile(
        r"\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|DROP|ALTER|CREATE|"
        r"TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|EXECUTE|"
        r"VACUUM|ANALYZE|REFRESH|SET|RESET|COMMIT|ROLLBACK|"
        r"INTO|LOCK)\b",
        re.IGNORECASE,
    )

    if proibidos.search(consulta):
        return "Consulta bloqueada: comando ou expressão não permitido."

    # Evita múltiplas instruções SQL.
    if ";" in consulta:
        return "Consulta bloqueada: execute uma instrução por vez."

    # Evita funções capazes de acessar arquivos ou executar comandos.
    funcoes_proibidas = re.compile(
        r"\b(pg_read_file|pg_read_binary_file|pg_ls_dir|"
        r"pg_write_file|pg_terminate_backend|pg_cancel_backend|"
        r"lo_import|lo_export|dblink|dblink_exec)\s*\(",
        re.IGNORECASE,
    )

    if funcoes_proibidas.search(consulta):
        return "Consulta bloqueada: função não permitida."

    # Limita o volume retornado, sem alterar consultas que já têm LIMIT.
    if not re.search(r"\bLIMIT\b", consulta, re.IGNORECASE):
        consulta += " LIMIT 100"

    try:
        async with motor_negocio.connect() as conexao:
            async with conexao.begin():
                await conexao.exec_driver_sql(
                    "SET TRANSACTION READ ONLY"
                )

                resultado = await conexao.execute(text(consulta))
                linhas = resultado.mappings().all()

        if not linhas:
            return "A consulta não retornou registros."

        return "\n".join(
            str(dict(linha))
            for linha in linhas
        )

    except Exception:
        # Não expõe detalhes internos nem credenciais do banco.
        return (
            "Não foi possível executar a consulta. "
            "Verifique os nomes das tabelas, colunas e os tipos de dados."
        )
