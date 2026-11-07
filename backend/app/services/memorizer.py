import json
import logging
from sqlalchemy import text
from app.db.session import SessaoBanco
from app.core.config import obter_provedor_embeddings

logger = logging.getLogger("multiagentes.memorizer")

async def memorizar_resposta(pergunta: str, resposta: str) -> None:
    try:
        embedder = obter_provedor_embeddings()
        conteudo_memoria = f"Pergunta: {pergunta}\nResposta: {resposta}"
        
        # Gera embedding via Jina AI v3
        vetor = embedder.embed_query(conteudo_memoria)
        
        async with SessaoBanco() as sessao:
            # Insere registro no documento pai
            res = await sessao.execute(
                text("INSERT INTO documentos (titulo, conteudo) VALUES ('Memória Dinâmica', :c) RETURNING id"),
                {"c": conteudo_memoria}
            )
            doc_id = res.scalar()

            # Insere o chunk vetorial
            await sessao.execute(
                text("""
                    INSERT INTO documentos_chunks (documento_id, indice_chunk, conteudo, embedding)
                    VALUES (:doc_id, 0, :conteudo, :embedding)
                """),
                {
                    "doc_id": doc_id,
                    "conteudo": conteudo_memoria,
                    "embedding": json.dumps(vetor)
                }
            )
            await sessao.commit()
            logger.info("Novo conhecimento memorizado no PGVector com sucesso!")

    except Exception as e:
        logger.error(f"Falha ao salvar memória vetorial: {e}")