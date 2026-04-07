import sys
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

# Adiciona a pasta raiz ao caminho para o Python encontrar a pasta 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app import models

app = create_app()

with app.app_context():
    # Cria as tabelas se não existirem
    db.create_all()

    # 1. Inserir Tipos de Pessoa
    if not models.TipoPessoa.query.first():
        db.session.add_all([
            models.TipoPessoa(descricao="Professor"),
            models.TipoPessoa(descricao="Aluno"),
            models.TipoPessoa(descricao="Administrador")
        ])
        db.session.commit()
        print("Tipos de Pessoa inseridos com sucesso!")

    # 2. Inserir o Primeiro Professor (Admin Padrão)
    if not models.Usuario.query.first():
        tipo_prof = models.TipoPessoa.query.filter_by(descricao="Professor").first()

        # Cria a senha criptografada para o primeiro acesso
        senha_hash = generate_password_hash("senha123")
        
        novo_usuario = models.Usuario(
            id_tipo=tipo_prof.id_tipo,
            nome_completo="Professor Admin (Semente)",
            data_nascimento=datetime.strptime('1986-03-12', '%Y-%m-%d').date(),
            email="admin@unilab.edu.br",
            senha_hash=senha_hash,
            ativo=True
        )
        db.session.add(novo_usuario)
        db.session.flush() # Guarda temporariamente para gerar o id_usuario

        novo_professor = models.Professor(
            id_usuario=novo_usuario.id_usuario,
            registro_profissional="OM-MASTER-001"
        )
        db.session.add(novo_professor)
        db.session.commit()
        
        print("Primeiro Professor criado com sucesso!")
        print("Email: admin@unilab.edu.br")
        print("Senha: senha123")
    else:
        print("Banco de dados já configurado e pronto a usar!")