import logging
from sqlalchemy import text
from app.db.session import SessaoBanco

logger = logging.getLogger("multiagentes.services")


async def obter_historico_do_apredizado() -> list[dict]:
    """Retorna todas as memórias registradas no banco PGVector sem quebrar a requisição."""
    try:
        async with SessaoBanco() as sessao:
            sql = text("""
                SELECT id, conteudo, criado_em 
                FROM documentos_chunks 
                ORDER BY id DESC
            """)
            resultado = await sessao.execute(sql)
            linhas = resultado.mappings().all()

        historico = []
        for linha in linhas:
            try:
                conteudo = str(linha["conteudo"])
                pergunta = conteudo
                resposta = ""

                # Parsing resiliente que aceita variações de caixa (Pergunta vs pergunta)
                if "pergunta:" in conteudo.lower() and "resposta:" in conteudo.lower():
                    # Procura case-insensitive
                    idx_resposta = conteudo.lower().find("resposta:")
                    pergunta_raw = conteudo[:idx_resposta]
                    resposta_raw = conteudo[idx_resposta:]

                    pergunta = pergunta_raw.replace("Pergunta:", "").replace("pergunta:", "").strip()
                    resposta = resposta_raw.replace("Resposta:", "").replace("resposta:", "").strip()

                historico.append({
                    "id": linha["id"],
                    "pergunta": pergunta,
                    "resposta": resposta,
                    "criado_em": str(linha["criado_em"]) if linha.get("criado_em") is not None else ""
                })
            except Exception as err_item:
                logger.warning(f"Erro ao processar item {linha.get('id')}: {err_item}")
                continue

        return historico
    except Exception as e:
        logger.error(f"Erro crítico ao obter histórico de aprendizado: {e}")
        return []