-- Migração: adiciona coluna sequencia_livre à tabela atividade
-- Executar uma única vez no banco de produção/desenvolvimento

ALTER TABLE atividade
  ADD COLUMN IF NOT EXISTS sequencia_livre BOOLEAN NOT NULL DEFAULT FALSE;
