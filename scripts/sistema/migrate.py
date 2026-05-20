"""
Executa todas as migrações do banco em ordem.
Cada etapa é idempotente — seguro re-executar quantas vezes quiser.

Uso:
    python scripts/migrate.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models import Aluno, Usuario
from sqlalchemy import text

app = create_app()

def ok(msg):  print(f"  [OK] {msg}")
def skip(msg): print(f"  [--] {msg}")

with app.app_context():

    # ── M001 — Criar todas as tabelas definidas nos modelos ───────────────
    print("M001: criar tabelas base")
    db.create_all()
    ok("Todas as tabelas criadas/verificadas.")

    # ── M002 — Adicionar coluna `login` em `aluno` ────────────────────────
    print("M002: coluna login em aluno")
    col_existe = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='aluno' AND column_name='login'"
    )).scalar()
    if not col_existe:
        db.session.execute(text("ALTER TABLE aluno ADD COLUMN login VARCHAR(80) UNIQUE"))
        db.session.commit()
        ok("Coluna 'login' adicionada.")
    else:
        skip("Coluna 'login' já existe.")

    # Preenche alunos sem login com a parte antes do @ do e-mail
    alunos_sem_login = Aluno.query.filter(
        (Aluno.login == None) | (Aluno.login == '')
    ).all()
    atualizados = 0
    for aluno in alunos_sem_login:
        usr = Usuario.query.get(aluno.id_usuario)
        if usr:
            base = usr.email.split('@')[0]
            candidato, sufixo = base, 1
            while Aluno.query.filter(Aluno.login == candidato,
                                     Aluno.id_aluno != aluno.id_aluno).first():
                candidato = f"{base}{sufixo}"; sufixo += 1
            aluno.login = candidato
            atualizados += 1
    db.session.commit()
    if atualizados:
        ok(f"{atualizados} aluno(s) preenchidos com login derivado do e-mail.")

    # ── M003 — Adicionar coluna `caminho_preview` em `mapa` ──────────────
    print("M003: coluna caminho_preview em mapa")
    try:
        db.session.execute(text(
            "ALTER TABLE mapa ADD COLUMN IF NOT EXISTS caminho_preview VARCHAR(500)"
        ))
        db.session.commit()
        ok("Coluna 'caminho_preview' adicionada.")
    except Exception as e:
        db.session.rollback()
        skip(f"caminho_preview: {e}")

    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    previews_dir  = os.path.join(upload_folder, 'previews')
    os.makedirs(previews_dir, exist_ok=True)
    ok(f"Pasta de previews garantida: {previews_dir}")

    # ── M004 — Adicionar coluna `caminho_render_3d` em `mapa` ────────────
    print("M004: coluna caminho_render_3d em mapa")
    col_existe = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='mapa' AND column_name='caminho_render_3d'"
    )).scalar()
    if not col_existe:
        db.session.execute(text(
            "ALTER TABLE mapa ADD COLUMN caminho_render_3d VARCHAR(500)"
        ))
        db.session.commit()
        renders_dir = os.path.join(upload_folder, 'renders3d')
        os.makedirs(renders_dir, exist_ok=True)
        ok(f"Coluna 'caminho_render_3d' adicionada. Pasta: {renders_dir}")
    else:
        skip("Coluna 'caminho_render_3d' já existe.")

    # ── M005 — Adicionar colunas id_atividade, dados_log e caminho_minimap em log_sessao ──
    print("M005: colunas id_atividade, dados_log e caminho_minimap em log_sessao")
    for col_sql, col_name in [
        ("id_atividade INTEGER REFERENCES atividade(id_atividade)", "id_atividade"),
        ("dados_log JSONB",                                          "dados_log"),
        ("caminho_minimap VARCHAR(500)",                             "caminho_minimap"),
    ]:
        existe = db.session.execute(text(
            "SELECT 1 FROM information_schema.columns "
            f"WHERE table_name='log_sessao' AND column_name='{col_name}'"
        )).scalar()
        if not existe:
            db.session.execute(text(f"ALTER TABLE log_sessao ADD COLUMN {col_sql}"))
            db.session.commit()
            ok(f"Coluna '{col_name}' adicionada.")
        else:
            skip(f"Coluna '{col_name}' já existe.")

    minimaps_dir = os.path.join(upload_folder, 'minimaps')
    os.makedirs(minimaps_dir, exist_ok=True)
    ok(f"Pasta de minimaps garantida: {minimaps_dir}")

    sessoes_dir = os.path.join(upload_folder, 'sessoes')
    os.makedirs(sessoes_dir, exist_ok=True)
    ok(f"Pasta de sessoes garantida: {sessoes_dir}")

    # ── M006 — Adicionar coluna `sequencia_livre` em `atividade` ─────────
    print("M006: coluna sequencia_livre em atividade")
    existe = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='atividade' AND column_name='sequencia_livre'"
    )).scalar()
    if not existe:
        db.session.execute(text(
            "ALTER TABLE atividade ADD COLUMN sequencia_livre BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        db.session.commit()
        ok("Coluna 'sequencia_livre' adicionada.")
    else:
        skip("Coluna 'sequencia_livre' já existe.")

    # ── M007 — Adicionar campos de contato em `aluno` ────────────────────
    print("M007: campos de contato em aluno (telefone, cep, logradouro)")
    for col_sql, col_name in [
        ("telefone VARCHAR(20)",    "telefone"),
        ("cep VARCHAR(9)",          "cep"),
        ("logradouro VARCHAR(300)", "logradouro"),
    ]:
        existe = db.session.execute(text(
            "SELECT 1 FROM information_schema.columns "
            f"WHERE table_name='aluno' AND column_name='{col_name}'"
        )).scalar()
        if not existe:
            db.session.execute(text(f"ALTER TABLE aluno ADD COLUMN {col_sql}"))
            db.session.commit()
            ok(f"Coluna '{col_name}' adicionada em aluno.")
        else:
            skip(f"aluno.{col_name} já existe.")

    # ── M008 — Adicionar campos de endereço em `professor` ───────────────
    print("M008: campos de endereço em professor")
    for col_sql, col_name in [
        ("tipo_endereco VARCHAR(20)",   "tipo_endereco"),
        ("nome_instituicao VARCHAR(200)", "nome_instituicao"),
        ("cep VARCHAR(9)",              "cep"),
        ("logradouro VARCHAR(300)",     "logradouro"),
    ]:
        existe = db.session.execute(text(
            "SELECT 1 FROM information_schema.columns "
            f"WHERE table_name='professor' AND column_name='{col_name}'"
        )).scalar()
        if not existe:
            db.session.execute(text(f"ALTER TABLE professor ADD COLUMN {col_sql}"))
            db.session.commit()
            ok(f"Coluna '{col_name}' adicionada em professor.")
        else:
            skip(f"professor.{col_name} já existe.")

    # ── M009 — Adicionar datas de ciclo de vida em `atividade` ───────────
    print("M009: datas de ciclo de vida em atividade (previsao, finalizacao)")
    for col_sql, col_name in [
        ("data_previsao_finalizacao DATE",      "data_previsao_finalizacao"),
        ("data_finalizacao TIMESTAMP",          "data_finalizacao"),
    ]:
        existe = db.session.execute(text(
            "SELECT 1 FROM information_schema.columns "
            f"WHERE table_name='atividade' AND column_name='{col_name}'"
        )).scalar()
        if not existe:
            db.session.execute(text(f"ALTER TABLE atividade ADD COLUMN {col_sql}"))
            db.session.commit()
            ok(f"Coluna '{col_name}' adicionada em atividade.")
        else:
            skip(f"atividade.{col_name} já existe.")

    # ── M010 — Adicionar coluna `ativo` em `mapa` ────────────────────────
    print("M010: coluna ativo em mapa")
    existe = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='mapa' AND column_name='ativo'"
    )).scalar()
    if not existe:
        db.session.execute(text(
            "ALTER TABLE mapa ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        db.session.commit()
        ok("Coluna 'ativo' adicionada em mapa.")
    else:
        skip("mapa.ativo já existe.")

    # ── M011 — Adicionar coluna `id_mapa_original` em `mapa` ─────────────
    print("M011: coluna id_mapa_original em mapa")
    existe = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='mapa' AND column_name='id_mapa_original'"
    )).scalar()
    if not existe:
        db.session.execute(text(
            "ALTER TABLE mapa ADD COLUMN id_mapa_original INTEGER REFERENCES mapa(id_mapa)"
        ))
        db.session.commit()
        ok("Coluna 'id_mapa_original' adicionada em mapa.")
    else:
        skip("mapa.id_mapa_original já existe.")

    print("\nMigrações concluídas.")
