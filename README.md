# API OM — Orientação e Mobilidade

API REST em Flask para o sistema de **Orientação e Mobilidade (OM)**, que gerencia professores, alunos, mapas, sessões de treino e análises.

## Tecnologias

- Python 3 + Flask
- Flask-SQLAlchemy (PostgreSQL)
- Flask-JWT-Extended
- Flask-CORS
- Swagger UI (`/docs`)

## Estrutura

```
api-om/
├── app/
│   ├── __init__.py         # Fábrica da aplicação
│   ├── models.py           # Modelos SQLAlchemy
│   ├── routes/
│   │   ├── auth.py         # Login e cadastro de professor
│   │   ├── alunos.py       # CRUD de alunos
│   │   ├── professores.py  # Gestão de professores (admin)
│   │   ├── treinos.py      # Mapas e sessões de treino
│   │   ├── atividades.py   # Atividades atribuídas a alunos
│   │   └── analises.py     # Métricas por sessão
│   ├── static/
│   │   └── swagger.yaml    # Documentação OpenAPI 3.0
│   └── utils.py
├── scripts/
│   ├── init_db.py
│   ├── migrate_add_login.py
│   ├── migrate_add_preview.py
│   └── migrate_add_atividades.py
└── run.py
```

## Configuração

1. Criar e ativar o ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Instalar dependências:
   ```bash
   pip install -r app/requirements.txt
   ```

3. Configurar o banco no `app/__init__.py`:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://usuario:senha@localhost:5432/om_database'
   ```

4. Inicializar o banco:
   ```bash
   python scripts/init_db.py
   ```

5. Executar:
   ```bash
   python run.py
   ```

## Documentação

Após iniciar, acesse: [http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs)

## Rotas principais

| Tag | Base URL |
|---|---|
| Autenticação | `/api/auth` |
| Alunos | `/api/alunos` |
| Professores (admin) | `/api/professores` |
| Mapas e Treinos | `/api/treinos` |
| Atividades | `/api/atividades` |
| Análises | `/api/analises` |
