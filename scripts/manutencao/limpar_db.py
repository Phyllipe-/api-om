"""
Limpa o banco de dados, mantendo apenas o usuário inicial (id_usuario = 1)
e seu registro de professor associado.

Uso:
    python scripts/limpar_db.py
    python scripts/limpar_db.py --confirmar   # pula confirmação interativa
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():

    # ── Contagens antes ───────────────────────────────────────────────────
    tabelas = [
        "comparacao", "giros", "trafego", "simulacao_trajetoria", "lateralidade",
        "log_sessao", "atividade_aluno", "atividade_mapa", "atividade",
        "mapa", "aluno", "professor", "usuario",
    ]

    print("Estado atual do banco:")
    for t in tabelas:
        count = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        print(f"  {t}: {count}")

    print()

    # ── Confirmação ───────────────────────────────────────────────────────
    if "--confirmar" not in sys.argv:
        resp = input("Tem certeza? Isso apaga TODOS os dados exceto id_usuario=1. Digite 'sim' para continuar: ")
        if resp.strip().lower() != "sim":
            print("Operação cancelada.")
            sys.exit(0)

    # ── Limpeza em ordem (respeita FKs) ──────────────────────────────────

    # 1. Análises (dependem de log_sessao)
    for t in ["comparacao", "giros", "trafego", "simulacao_trajetoria", "lateralidade"]:
        db.session.execute(text(f'DELETE FROM "{t}"'))

    # 2. Sessões
    db.session.execute(text('DELETE FROM "log_sessao"'))

    # 3. Vínculos de atividade
    db.session.execute(text('DELETE FROM "atividade_aluno"'))
    db.session.execute(text('DELETE FROM "atividade_mapa"'))

    # 4. Atividades
    db.session.execute(text('DELETE FROM "atividade"'))

    # 5. Mapas
    db.session.execute(text('DELETE FROM "mapa"'))

    # 6. Alunos (e seus usuários)
    alunos_ids = [r[0] for r in db.session.execute(text('SELECT id_usuario FROM "aluno"')).fetchall()]
    db.session.execute(text('DELETE FROM "aluno"'))

    # 7. Professores extras (id_usuario != 1)
    profs_ids = [r[0] for r in db.session.execute(
        text('SELECT id_usuario FROM "professor" WHERE id_usuario != 1')
    ).fetchall()]
    db.session.execute(text('DELETE FROM "professor" WHERE id_usuario != 1'))

    # 8. Usuários extras (mantém id_usuario = 1)
    ids_remover = list(set(alunos_ids + profs_ids))
    if ids_remover:
        placeholders = ", ".join(str(i) for i in ids_remover)
        db.session.execute(text(f'DELETE FROM "usuario" WHERE id_usuario IN ({placeholders})'))

    db.session.commit()

    # ── Contagens depois ──────────────────────────────────────────────────
    print("\nEstado após limpeza:")
    for t in tabelas:
        count = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        print(f"  {t}: {count}")

    # Confirmar usuário remanescente
    usr = db.session.execute(text('SELECT id_usuario, email FROM "usuario"')).fetchall()
    print(f"\nUsuários remanescentes: {usr}")
    print("\nLimpeza concluída.")
