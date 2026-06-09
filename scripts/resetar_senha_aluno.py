#!/usr/bin/env python
"""
Reseta a senha de um aluno específico.

Uso:
    python scripts/resetar_senha_aluno.py <id_aluno> <nova_senha>

Exemplo:
    python scripts/resetar_senha_aluno.py 1 sigoud
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import Aluno, Usuario

def resetar_senha(id_aluno, nova_senha):
    app = create_app()
    with app.app_context():
        aluno = Aluno.query.get(id_aluno)
        if not aluno:
            print(f"Erro: Aluno com ID {id_aluno} não encontrado")
            return False

        usuario = Usuario.query.get(aluno.id_usuario)
        if not usuario:
            print(f"Erro: Usuário do aluno {id_aluno} não encontrado")
            return False

        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()

        print(f"Senha resetada com sucesso!")
        print(f"Aluno: {aluno.nome_completo}")
        print(f"Email: {usuario.email}")
        print(f"Nova senha: {nova_senha}")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    try:
        id_aluno = int(sys.argv[1])
        nova_senha = sys.argv[2]
        resetar_senha(id_aluno, nova_senha)
    except ValueError:
        print("Erro: ID do aluno deve ser um número")
        sys.exit(1)
