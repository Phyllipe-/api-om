"""
seed_usuarios.py — Cenário demo: 2 professores + 2 alunos cada
==============================================================

Cria apenas cadastros básicos (sem mapas, sessões ou análises).
Imprime tabela com e-mail e senha ao final.

Uso:
    python scripts/demo/seed_usuarios.py
    python scripts/demo/seed_usuarios.py --limpar   # remove cadastros demo antes de inserir
"""

import sys, os, argparse
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import TipoPessoa, Usuario, Professor, Aluno

app = create_app()

# ── Dados do cenário ──────────────────────────────────────────────────────────

PROFESSORES = [
    {
        "nome":       "Fernanda Oliveira",
        "email":      "fernanda.oliveira@om.edu.br",
        "senha":      "prof1234",
        "nascimento": date(1985, 6, 14),
        "registro":   "OM-PROF-001",
    },
    {
        "nome":       "Ricardo Mendes",
        "email":      "ricardo.mendes@om.edu.br",
        "senha":      "prof5678",
        "nascimento": date(1979, 11, 3),
        "registro":   "OM-PROF-002",
    },
]

# Dois alunos por professor (índice 0 → Fernanda, índice 1 → Ricardo)
ALUNOS = [
    {
        "nome":        "Beatriz Santos",
        "email":       "beatriz.santos@aluno.om.br",
        "senha":       "aluno1234",
        "nascimento":  date(2010, 3, 22),
        "escolaridade":"Ensino Fundamental II",
        "professor_idx": 0,
    },
    {
        "nome":        "Lucas Pereira",
        "email":       "lucas.pereira@aluno.om.br",
        "senha":       "aluno2345",
        "nascimento":  date(2009, 8, 7),
        "escolaridade":"Ensino Médio",
        "professor_idx": 0,
    },
    {
        "nome":        "Camila Rocha",
        "email":       "camila.rocha@aluno.om.br",
        "senha":       "aluno3456",
        "nascimento":  date(2011, 1, 15),
        "escolaridade":"Ensino Fundamental II",
        "professor_idx": 1,
    },
    {
        "nome":        "Diego Alves",
        "email":       "diego.alves@aluno.om.br",
        "senha":       "aluno4567",
        "nascimento":  date(2010, 5, 30),
        "escolaridade":"Ensino Médio",
        "professor_idx": 1,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _login(email):
    return email.split("@")[0]

def _limpar(tipo_prof, tipo_aluno):
    emails_demo = [p["email"] for p in PROFESSORES] + [a["email"] for a in ALUNOS]
    for email in emails_demo:
        usr = Usuario.query.filter_by(email=email).first()
        if not usr:
            continue
        aluno = Aluno.query.filter_by(id_usuario=usr.id_usuario).first()
        if aluno:
            db.session.delete(aluno)
        prof = Professor.query.filter_by(id_usuario=usr.id_usuario).first()
        if prof:
            db.session.delete(prof)
        db.session.delete(usr)
    db.session.commit()
    print("Cadastros demo anteriores removidos.\n")

# ── Main ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--limpar", action="store_true")
args = parser.parse_args()

with app.app_context():

    tipo_prof  = TipoPessoa.query.filter_by(descricao="Professor").first()
    tipo_aluno = TipoPessoa.query.filter_by(descricao="Aluno").first()

    if not tipo_prof or not tipo_aluno:
        print("Tipos de pessoa não encontrados. Execute sistema/init_db.py primeiro.")
        sys.exit(1)

    if args.limpar:
        _limpar(tipo_prof, tipo_aluno)

    # Criar professores
    prof_objs = []
    for p in PROFESSORES:
        if Usuario.query.filter_by(email=p["email"]).first():
            print(f"[--] Professor já existe: {p['email']}")
            usr = Usuario.query.filter_by(email=p["email"]).first()
            prof_objs.append(Professor.query.filter_by(id_usuario=usr.id_usuario).first())
            continue

        usr = Usuario(
            id_tipo=tipo_prof.id_tipo,
            nome_completo=p["nome"],
            email=p["email"],
            senha_hash=generate_password_hash(p["senha"]),
            data_nascimento=p["nascimento"],
            ativo=True,
        )
        db.session.add(usr)
        db.session.flush()

        prof = Professor(id_usuario=usr.id_usuario, registro_profissional=p["registro"])
        db.session.add(prof)
        db.session.flush()
        prof_objs.append(prof)
        print(f"[OK] Professor criado: {p['nome']}")

    # Criar alunos
    for a in ALUNOS:
        if Usuario.query.filter_by(email=a["email"]).first():
            print(f"[--] Aluno já existe: {a['email']}")
            continue

        usr = Usuario(
            id_tipo=tipo_aluno.id_tipo,
            nome_completo=a["nome"],
            email=a["email"],
            senha_hash=generate_password_hash(a["senha"]),
            data_nascimento=a["nascimento"],
            ativo=True,
        )
        db.session.add(usr)
        db.session.flush()

        aluno = Aluno(
            id_usuario=usr.id_usuario,
            id_professor_responsavel=prof_objs[a["professor_idx"]].id_professor,
            escolaridade=a["escolaridade"],
            login=_login(a["email"]),
        )
        db.session.add(aluno)
        print(f"[OK] Aluno criado: {a['nome']} > {PROFESSORES[a['professor_idx']]['nome']}")

    db.session.commit()

    # ── Tabela de credenciais ─────────────────────────────────────────────
    print()
    print("=" * 72)
    print(f"{'Perfil':<10} {'Nome':<22} {'E-mail':<36} {'Senha'}")
    print("-" * 72)

    admin = Usuario.query.get(1)
    if admin:
        print(f"{'Admin':<10} {admin.nome_completo:<22} {admin.email:<36} (senha cadastrada)")

    for p in PROFESSORES:
        print(f"{'Professor':<10} {p['nome']:<22} {p['email']:<36} {p['senha']}")

    print("-" * 72)

    for a in ALUNOS:
        prof_nome = PROFESSORES[a["professor_idx"]]["nome"].split()[0]
        print(f"{'Aluno':<10} {a['nome']:<22} {a['email']:<36} {a['senha']}  (resp: {prof_nome})")

    print("=" * 72)
    print()
