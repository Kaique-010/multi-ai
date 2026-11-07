
-- 1. Habilita a extensão para armazenar e pesquisar vetores.
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Armazena documentos que serão consultados pelos agentes.
CREATE TABLE IF NOT EXISTS documentos (
    id BIGSERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    origem VARCHAR(500),
    metadados JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Registra o processamento dos documentos.
-- Útil para rastrear importações e evitar reprocessamento desnecessário.
CREATE TABLE IF NOT EXISTS documentos_processamentos (
    id BIGSERIAL PRIMARY KEY,
    documento_id BIGINT NOT NULL
        REFERENCES documentos(id) ON DELETE CASCADE,
    hash_conteudo VARCHAR(64) NOT NULL,
    modelo_embedding VARCHAR(150) NOT NULL,
    dimensao_embedding INTEGER NOT NULL CHECK (dimensao_embedding > 0),
    processado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (documento_id, hash_conteudo, modelo_embedding)
);

-- 4. Índices para consultas e filtros.
CREATE INDEX IF NOT EXISTS idx_documentos_titulo
    ON documentos (titulo);

CREATE INDEX IF NOT EXISTS idx_documentos_criado_em
    ON documentos (criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_documentos_metadados
    ON documentos USING GIN (metadados);

CREATE INDEX IF NOT EXISTS idx_processamentos_documento
    ON documentos_processamentos (documento_id);



-- 5. Armazena os trechos (chunks) dos documentos com seus respectivos vetores.
-- Usamos dimensão 1024 (padrão do jina-embeddings-v3)
CREATE TABLE IF NOT EXISTS documentos_chunks (
    id BIGSERIAL PRIMARY KEY,
    documento_id BIGINT NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    indice_chunk INTEGER NOT NULL,
    conteudo TEXT NOT NULL,
    metadados JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1024) NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Índices para otimização de busca vetorial e navegação
CREATE INDEX IF NOT EXISTS idx_chunks_documento_id 
    ON documentos_chunks (documento_id);

-- Índice HNSW no pgvector para busca por similaridade de cosseno ultrarrápida
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
    ON documentos_chunks USING hnsw (embedding vector_cosine_ops);