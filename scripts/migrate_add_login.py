"""
Migração: adiciona coluna `login` à tabela `aluno` e preenche registros existentes.

Uso:
    cd dashboard/api-om
    python scripts/migrate_add_login.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Aluno, Usuario
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 1. Adiciona a coluna se ainda não existir
    try:
        db.session.execute(text("ALTER TABLE aluno ADD COLUMN login VARCHAR(80) UNIQUE"))
        db.session.commit()
        print("Coluna 'login' adicionada.")
    except Exception as e:
        db.session.rollback()
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("Coluna 'login' já existe — pulando ALTER TABLE.")
        else:
            raise

    # 2. Preenche alunos sem login com a parte antes do @ do email
    alunos_sem_login = Aluno.query.filter(
        (Aluno.login == None) | (Aluno.login == '')
    ).all()

    atualizados = 0
    for aluno in alunos_sem_login:
        usr = Usuario.query.get(aluno.id_usuario)
        if usr:
            base = usr.email.split('@')[0]
            # Garante unicidade: se base já existe, adiciona sufixo numérico
            candidato = base
            sufixo = 1
            while Aluno.query.filter(Aluno.login == candidato, Aluno.id_aluno != aluno.id_aluno).first():
                candidato = f"{base}{sufixo}"
                sufixo += 1
            aluno.login = candidato
            atualizados += 1

    db.session.commit()
    print(f"{atualizados} aluno(s) atualizados com login derivado do email.")
    print("Migração concluída.")
