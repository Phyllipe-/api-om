"""
Cria as tabelas atividade, atividade_mapa, atividade_aluno (se não existirem).
Execute: python scripts/migrate_add_atividades.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db

app = create_app()
with app.app_context():
    db.create_all()
    print("Tabelas criadas/verificadas com sucesso.")
