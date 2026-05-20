-- Migration: add_quadros
-- Cria tabelas de catálogo de quadros e preferências por usuário

CREATE TABLE IF NOT EXISTS quadro (
    id             SERIAL PRIMARY KEY,
    chave          VARCHAR(80)  NOT NULL UNIQUE,
    nome           VARCHAR(150) NOT NULL,
    secao          VARCHAR(30)  NOT NULL,   -- esquerda | centro | direita | multi
    tamanho        VARCHAR(20)  NOT NULL,   -- fixo | pequeno | medio | grande
    ordem_padrao   INTEGER      NOT NULL DEFAULT 0,
    ativo_padrao   BOOLEAN      NOT NULL DEFAULT TRUE,
    personalizavel BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS preferencia_quadro (
    id           SERIAL PRIMARY KEY,
    id_usuario   INTEGER     NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    chave_quadro VARCHAR(80) NOT NULL REFERENCES quadro(chave)       ON DELETE CASCADE,
    visivel      BOOLEAN     NOT NULL DEFAULT TRUE,
    ordem        INTEGER,
    CONSTRAINT uq_pref_usuario_quadro UNIQUE (id_usuario, chave_quadro)
);

-- Seed: 19 quadros do perfil-aluno
INSERT INTO quadro (chave, nome, secao, tamanho, ordem_padrao, ativo_padrao, personalizavel) VALUES
  -- Coluna esquerda (menu lateral) — não personalizáveis
  ('aluno',                'Aluno',                    'esquerda', 'fixo',    1, true,  false),
  ('filtro-sessoes',       'Filtro de Sessões',         'esquerda', 'fixo',    2, true,  false),
  ('filtros-mapas',        'Filtros dos Mapas',         'esquerda', 'fixo',    3, true,  false),
  ('detalhes-atividade',   'Detalhes da Atividade',     'esquerda', 'fixo',    4, true,  true),
  ('analise-segmento',     'Análise de Segmento',       'esquerda', 'fixo',    5, true,  true),
  ('simulador-trajetoria', 'Simulador de Trajetória',   'esquerda', 'fixo',    6, true,  true),

  -- Coluna centro
  ('mapa-giros',           'Mapa de Giros',             'centro',   'medio',   1, true,  true),
  ('eventos-area',         'Eventos por Área',          'centro',   'medio',   2, true,  true),
  ('colisoes-percurso',    'Colisões no Percurso',      'centro',   'medio',   3, true,  true),
  ('mapa-permanencia',     'Mapa de Permanência',       'centro',   'medio',   4, true,  true),

  -- Coluna direita
  ('mapa-lateralidade',    'Mapa da Lateralidade',      'direita',  'pequeno', 1, true,  true),
  ('analise-comportamental','Análise Comportamental',   'direita',  'pequeno', 2, true,  true),

  -- Seção Sessões Múltiplas — coluna direita (pequenos)
  ('lat-por-sessoes',      'Lateralidade por Sessões',  'multi',    'pequeno', 1, true,  true),
  ('col-por-sessao',       'Colisões por Sessão',       'multi',    'pequeno', 2, true,  true),
  ('giros-detalhado',      'Giros por Sessão Detalhado','multi',    'pequeno', 3, true,  true),

  -- Seção Sessões Múltiplas — coluna centro (grandes)
  ('giros-por-sessao',     'Giros por Sessão',          'multi',    'grande',  4, true,  true),
  ('dist-menor-caminho',   'Distância Percorrida vs Menor Caminho', 'multi', 'grande', 5, true, true),
  ('col-giros-sessao',     'Colisões e Giros por Sessão','multi',   'grande',  6, true,  true),
  ('evolucao-sessao',      'Evolução por Sessão',       'multi',    'grande',  7, true,  true)

ON CONFLICT (chave) DO NOTHING;
