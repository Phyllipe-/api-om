"""
Limpa o banco de dados, mantendo apenas o usuário inicial (id_usuario = 1)
e seu registro de professor associado.

Tabelas de REFERÊNCIA são preservadas: tipo_pessoa, quadro.

Uso:
    python scripts/manutencao/limpar_db.py
    python scripts/manutencao/limpar_db.py --confirmar   # pula confirmação interativa
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text

app = create_app()

# Ordem de exclusão (filhos → pais), respeitando as FKs do schema atual.
# NÃO inclui as tabelas de referência (tipo_pessoa, quadro), que são preservadas.
ORDEM_DELETE = [
    # análises (dependem de log_sessao)
    "comparacao", "giros", "lateralidade", "simulacao_trajetoria", "trafego",
    # sessões
    "log_sessao",
    # vínculos e avaliações (dependem de atividade/mapa/professor)
    "atividade_aluno", "atividade_mapa", "avaliacao_mapa",
    # atividades e mapas
    "atividade", "mapa",
    # preferências de quadro por usuário
    "preferencia_quadro",
    # alunos
    "aluno",
]

# Tabelas mostradas nas contagens (dados operacionais).
TABELAS_DADOS = ORDEM_DELETE + ["professor", "usuario"]
# Tabelas de referência preservadas.
TABELAS_REFERENCIA = ["tipo_pessoa", "quadro"]


def contar(rotulo):
    print(rotulo)
    for t in TABELAS_DADOS:
        c = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        print(f"  {t}: {c}")
    print("  -- referência (preservadas) --")
    for t in TABELAS_REFERENCIA:
        c = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        print(f"  {t}: {c}")


with app.app_context():

    contar("Estado atual do banco:")
    print()

    # ── Confirmação ───────────────────────────────────────────────────────
    if "--confirmar" not in sys.argv:
        resp = input("Tem certeza? Isso apaga TODOS os dados exceto id_usuario=1. Digite 'sim' para continuar: ")
        if resp.strip().lower() != "sim":
            print("Operação cancelada.")
            sys.exit(0)

    # ── Limpeza atômica em ordem de FK ────────────────────────────────────
    try:
        for t in ORDEM_DELETE:
            db.session.execute(text(f'DELETE FROM "{t}"'))

        # Professores e usuários extras (mantém id_usuario = 1)
        db.session.execute(text('DELETE FROM "professor" WHERE id_usuario != 1'))
        db.session.execute(text('DELETE FROM "usuario" WHERE id_usuario != 1'))

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    print()
    contar("Estado após limpeza:")

    usr = db.session.execute(text('SELECT id_usuario, email FROM "usuario" ORDER BY id_usuario')).fetchall()
    print(f"\nUsuários remanescentes: {usr}")
    print("\nLimpeza concluída.")
