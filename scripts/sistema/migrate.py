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

    print("\nMigrações concluídas.")
