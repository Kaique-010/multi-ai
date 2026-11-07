import asyncio
import json
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_distances
from sqlalchemy import text

from app.db.session import SessaoBanco


async def extrair_e_analisar_cerebro():
    print("🧠 Lendo as memórias do PGVector...")

    async with SessaoBanco() as sessao:
        sql = text("""
            SELECT id, conteudo, embedding::text 
            FROM documentos_chunks
            ORDER BY id ASC
        """)
        resultado = await sessao.execute(sql)
        linhas = resultado.fetchall()

    if not linhas:
        print("⚠️ Nenhuma memória encontrada na tabela 'documentos_chunks'.")
        return

    ids = [l.id for l in linhas]
    # Extrai o texto limpo para exibir como rótulo visual
    textos = [l.conteudo.replace("\n", " ") for l in linhas]
    textos_curtos = [f"[{l.id}] {l.conteudo[:40]}..." for l in linhas]
    vetores = np.array([json.loads(l.embedding) for l in linhas])

    print(f"\n✅ Encontradas {len(vetores)} memórias salvas no 'cérebro'.\n")

    # --- 1. MATRIZ DE DISTÂNCIA DE COSSENO ---
    # Calcula a distância entre todos os pares de vetores (0.0 = idêntico, 1.0 = oposto)
    matriz_distancia = cosine_distances(vetores)

    df_distancia = pd.DataFrame(
        matriz_distancia, 
        index=[f"ID_{i}" for i in ids], 
        columns=[f"ID_{i}" for i in ids]
    )

    print("==========================================================================")
    print("      📐 MATRIZ DE DISTÂNCIA DE COSSENO ENTRE AS MEMÓRIAS (Jina v3)")
    print("==========================================================================")
    print(df_distancia.round(4))
    print("--------------------------------------------------------------------------")
    print("💡 Legenda: Quanto menor a distância (< 0.35), mais semanticamente similares!")
    print("==========================================================================\n")

    # Lista pares e suas distâncias
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            dist = matriz_distancia[i][j]
            print(f"🔹 Distância entre [{ids[i]}] e [{ids[j]}]: {dist:.4f}")
            print(f"   ├─ M1: {textos_curtos[i]}")
            print(f"   └─ M2: {textos_curtos[j]}\n")

    # --- 2. GRÁFICO 2D INTERATIVO COM TEXTOS VISÍVEIS ---
    n_componentes = min(2, len(vetores))
    if n_componentes < 2:
        print("⚠️ Insira pelo menos 2 memórias para gerar o gráfico visual.")
        return

    pca = PCA(n_components=2)
    vetores_2d = pca.fit_transform(vetores)

    df_plot = pd.DataFrame(vetores_2d, columns=["Componente_1", "Componente_2"])
    df_plot["ID"] = [str(i) for i in ids]
    df_plot["Texto_Completo"] = textos
    df_plot["Rotulo_Visivel"] = textos_curtos

    fig = px.scatter(
        df_plot,
        x="Componente_1",
        y="Componente_2",
        text="Rotulo_Visivel",
        color="ID",
        hover_name="Texto_Completo",
        title="🧠 Mapa do Cérebro Vetorial - Conceitos & Distâncias",
    )

    fig.update_traces(
        textposition="top center",
        marker=dict(size=14, symbol="circle")
    )
    fig.update_layout(
        showlegend=True,
        xaxis_title="Dimensão Semântica A",
        yaxis_title="Dimensão Semântica B"
    )

    output_html = "mapa_conhecimento_detalhado.html"
    fig.write_html(output_html)
    print(f"🌐 Visualizador salvo em '{output_html}'. Abra no seu navegador!")


if __name__ == "__main__":
    asyncio.run(extrair_e_analisar_cerebro())