-- Senha provisória: marca contas que precisam trocar a senha no primeiro login.
-- Aplicar em produção:  psql "$DATABASE_URL" -f migrations/add_senha_provisoria.sql
ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS senha_provisoria boolean NOT NULL DEFAULT false;
