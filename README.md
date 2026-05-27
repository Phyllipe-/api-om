# api-om

API REST em Flask para o sistema **Orientação e Mobilidade (OMA Project)**. Gerencia professores, alunos, mapas de treino, sessões e análises de desempenho.

Consumida por:
- **e3-react** — editor de mapas (professores)
- **dashboard-om** — dashboard de análise (professores)
- **ENA (Unity)** — app de treino (alunos)

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Framework | Flask 3 |
| Banco | PostgreSQL (SQLAlchemy 2) |
| Autenticação | JWT via Flask-JWT-Extended (4h de validade) |
| CORS | Flask-CORS — origens controladas por `ALLOWED_ORIGINS` |
| Rate limiting | Flask-Limiter |
| Docs | Swagger UI em `/docs` |
| Produção | Gunicorn |

## Pré-requisitos

- Python 3.10+
- PostgreSQL 14+ rodando localmente (ou URI remota)

## Configuração local

### 1. Ambiente virtual

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2. Dependências

```bash
pip install -r requirements.txt
# Para rodar testes:
pip install -r requirements-dev.txt
```

### 3. Variáveis de ambiente

Copie o arquivo de exemplo e preencha:

```bash
cp .env.example .env
```

```dotenv
# .env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/om_database
JWT_SECRET_KEY=troque-por-uma-chave-segura
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
FLASK_ENV=development
```

`ALLOWED_ORIGINS` lista as origens que podem chamar a API (separadas por vírgula). Em produção:

```dotenv
ALLOWED_ORIGINS=https://mova.omaproject.com.br,https://e3.omaproject.com.br
```

### 4. Banco de dados

Na primeira instalação:

```bash
python scripts/sistema/init_db.py   # cria tabelas + usuário admin inicial
python scripts/sistema/migrate.py   # aplica migrações de schema
```

Sempre que o schema mudar, rode `migrate.py` — ele é idempotente, seguro re-executar.

### 5. Executar

```bash
python run.py
```

API disponível em `http://127.0.0.1:5000`. Documentação interativa: `http://127.0.0.1:5000/docs`.

## Testes

```bash
pytest
```

Os testes ficam em `tests/`. Para verificar cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

## Estrutura

```
api-om/
├── app/
│   ├── __init__.py         # Fábrica da aplicação (CORS, JWT, Limiter, handlers)
│   ├── models.py           # Modelos SQLAlchemy
│   ├── utils.py            # Helpers compartilhados
│   ├── routes/
│   │   ├── auth.py         # POST /api/auth/login, /registro
│   │   ├── alunos.py       # CRUD /api/alunos
│   │   ├── professores.py  # /api/professores (somente admin)
│   │   ├── treinos.py      # /api/treinos/mapas, /sessoes, /arquivos
│   │   ├── atividades.py   # /api/atividades
│   │   └── analises.py     # /api/analises
│   └── static/
│       └── swagger.yaml    # Especificação OpenAPI 3.0
├── scripts/
│   ├── sistema/
│   │   ├── init_db.py      # Inicialização do banco (primeira vez)
│   │   └── migrate.py      # Migrações de schema (idempotente)
│   ├── demo/
│   │   └── seed_demo.py    # Dados fictícios para testes
│   └── manutencao/
│       └── limpar_db.py    # Remove dados (preserva admin)
├── tests/
├── uploads/                # Arquivos de mapa e previews (não commitado)
├── .env.example
├── requirements.txt
├── requirements-dev.txt
└── run.py
```

## Rotas

| Grupo | Base URL | Autenticação |
|---|---|---|
| Autenticação | `POST /api/auth/login` | Pública |
| Alunos | `/api/alunos` | JWT |
| Professores | `/api/professores` | JWT + admin |
| Mapas e Sessões | `/api/treinos` | JWT |
| Atividades | `/api/atividades` | JWT |
| Análises | `/api/analises` | JWT |

Ver todos os endpoints com exemplos de request/response em `/docs`.

## Scripts utilitários

| Script | Quando usar |
|---|---|
| `scripts/sistema/init_db.py` | Primeira instalação — cria tabelas e admin |
| `scripts/sistema/migrate.py` | Após qualquer mudança de schema |
| `scripts/demo/seed_demo.py` | Popula dados fictícios para demonstração |
| `scripts/demo/seed_demo.py --limpar` | Remove e repopula os dados de demo |
| `scripts/manutencao/limpar_db.py` | Remove todos os dados exceto o admin (`id=1`) |

## Deploy (produção — Oracle Cloud)

A API roda em Oracle Cloud Free Tier com Gunicorn + systemd.

```bash
# Instalar dependências no servidor
pip install -r requirements.txt

# Testar antes de subir o serviço
gunicorn -w 2 -b 127.0.0.1:5000 "app:create_app()"
```

O arquivo de serviço systemd está em `/etc/systemd/system/api-om.service`. Após atualizar o código:

```bash
git pull
pip install -r requirements.txt
python scripts/sistema/migrate.py
sudo systemctl restart api-om
```

## CI/CD

Não há pipeline automático para a API — o deploy é manual via SSH no Oracle Cloud. Isso é intencional enquanto não houver um runner self-hosted nessa instância.

## Pendências de segurança conhecidas

| # | Item | Impacto | Esforço |
|---|---|---|---|
| P1 | `/api/alunos/identificar` é público (sem JWT) | Enumeração de usuários | Decisão arquitetural pendente |
| P2 | Admin hardcoded como `id_usuario = 1` | Sem fallback se usuário 1 for deletado | ~1h (coluna `is_admin` + migration) |
| P3 | Logout não invalida token JWT | Token vivo por 4h mesmo após logout | ~2h (blocklist em Redis ou PostgreSQL) |
| P4 | Rate limiter em memória (sem Redis) | Reset ao reiniciar o processo | ~30min após Redis configurado |

Detalhes e soluções propostas: `dashboard/DEPLOY-NOTES.md`.
