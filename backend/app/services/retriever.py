import json
from sqlalchemy import text
from app.db.session import SessaoBanco
from app.core.config import obter_provedor_embeddings

async def buscar_contexto_com_score(
    query: str, 
    limite_distancia: float = 0.25
) -> tuple[str, float, bool]:
    """
    Retorna (contexto, score_distancia, encontrou_memoria).
    Score é a distância de cosseno (quanto menor, mais similar).
    """
    try:
        embedder = obter_provedor_embeddings()
        vetor_query = embedder.embed_query(query)

        async with SessaoBanco() as sessao:
            sql = text("""
                SELECT c.conteudo, (c.embedding <=> :vetor) AS distancia
                FROM documentos_chunks c
                ORDER BY distancia ASC
                LIMIT 1
            """)
            
            resultado = await sessao.execute(sql, {
                "vetor": json.dumps(vetor_query)
            })
            linha = resultado.fetchone()
            
            # Se não trouxe nada ou a distância ultrapassar o limite aceitável
            if not linha or linha.distancia > limite_distancia:
                score_retornado = float(linha.distancia) if linha else 1.0
                return "", score_retornado, False

            return str(linha.conteudo), float(linha.distancia), True

    except Exception:
        return "", 1.0, False   