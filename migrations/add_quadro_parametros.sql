-- Parâmetros configuráveis por quadro (JSON). Usado pela Análise Comportamental.
ALTER TABLE quadro ADD COLUMN IF NOT EXISTS parametros TEXT;
