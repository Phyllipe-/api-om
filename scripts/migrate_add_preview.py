"""
Adiciona a coluna `caminho_preview` à tabela `mapa`.
Execute uma única vez:
    python scripts/migrate_add_preview.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text(
                "ALTER TABLE mapa ADD COLUMN IF NOT EXISTS caminho_preview VARCHAR(500);"
            ))
            conn.commit()
            print("Coluna `caminho_preview` adicionada com sucesso.")
        except Exception as e:
            print(f"Aviso: {e}")

    # Garante que a pasta de previews existe
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    previews_dir  = os.path.join(upload_folder, 'previews')
    os.makedirs(previews_dir, exist_ok=True)
    print(f"Pasta de previews: {previews_dir}")
