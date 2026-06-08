-- Minimização LGPD: data de nascimento deixa de ser obrigatória; aluno passa a
-- registrar maioridade (menor_idade) + declaração do professor para menores.
-- Aplicar:  cd /opt/api-om && ./venv/bin/python -c "..."  (ou psql -f este arquivo)

ALTER TABLE usuario ALTER COLUMN data_nascimento DROP NOT NULL;

ALTER TABLE aluno ADD COLUMN IF NOT EXISTS menor_idade   boolean;
ALTER TABLE aluno ADD COLUMN IF NOT EXISTS declaracao_em  timestamp;
ALTER TABLE aluno ADD COLUMN IF NOT EXISTS declaracao_por integer;
