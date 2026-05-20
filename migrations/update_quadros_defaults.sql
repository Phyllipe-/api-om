-- Migration: update_quadros_defaults
-- Adiciona exclusivo_sessao_unica, atualiza ativo_padrao e ordem dos painéis

-- Nova coluna: painéis que só fazem sentido em modo sessão única
ALTER TABLE quadro ADD COLUMN IF NOT EXISTS exclusivo_sessao_unica BOOLEAN NOT NULL DEFAULT FALSE;

-- Marca os 3 painéis exclusivos de sessão única
UPDATE quadro SET exclusivo_sessao_unica = true
WHERE chave IN ('detalhes-atividade', 'analise-segmento', 'simulador-trajetoria');

-- Desabilita painéis fora do conjunto padrão
UPDATE quadro SET ativo_padrao = false
WHERE chave IN (
  'detalhes-atividade',
  'mapa-giros',
  'eventos-area',
  'colisoes-percurso',
  'giros-detalhado',
  'giros-por-sessao',
  'dist-menor-caminho',
  'col-giros-sessao'
);

-- Garante que os painéis padrão estejam habilitados
UPDATE quadro SET ativo_padrao = true
WHERE chave IN (
  'simulador-trajetoria',
  'analise-segmento',
  'mapa-permanencia',
  'mapa-lateralidade',
  'analise-comportamental',
  'lat-por-sessoes',
  'col-por-sessao',
  'evolucao-sessao'
);

-- Ordem na sidebar: Detalhes por último (único personalizável na esquerda)
UPDATE quadro SET ordem_padrao = 4 WHERE chave = 'detalhes-atividade';

-- Corrige secao: simulador e analise-segmento renderizam em colCentro, não na sidebar
UPDATE quadro SET secao = 'centro', tamanho = 'medio', ordem_padrao = 1 WHERE chave = 'simulador-trajetoria';
UPDATE quadro SET secao = 'centro', tamanho = 'medio', ordem_padrao = 2 WHERE chave = 'analise-segmento';
UPDATE quadro SET ordem_padrao = 3 WHERE chave = 'mapa-permanencia';
UPDATE quadro SET ordem_padrao = 4 WHERE chave = 'mapa-giros';
UPDATE quadro SET ordem_padrao = 5 WHERE chave = 'eventos-area';
UPDATE quadro SET ordem_padrao = 6 WHERE chave = 'colisoes-percurso';
