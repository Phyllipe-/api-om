-- Visibilidade de mapa (público/privado, padrão privado) + avaliações (0-3 estrelas).
ALTER TABLE mapa ADD COLUMN IF NOT EXISTS publico boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS avaliacao_mapa (
    id_avaliacao  SERIAL PRIMARY KEY,
    id_mapa       integer NOT NULL REFERENCES mapa(id_mapa),
    id_professor  integer NOT NULL REFERENCES professor(id_professor),
    nota          integer NOT NULL,
    data          timestamp DEFAULT now(),
    CONSTRAINT uq_avaliacao_mapa_prof UNIQUE (id_mapa, id_professor)
);
