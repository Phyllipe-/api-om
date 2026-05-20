"""
reset_cenario.py — Limpa o banco e recria exatamente o cenário de Cenario.md.

  Admin      Professor Phyllipe    phyllipe@om.edu.br     prof0000
  Professor  Fernanda Oliveira     fernanda@om.edu.br     prof1234
  Professor  Ricardo Mendes        ricardo@om.edu.br      prof5678
  Aluno      Beatriz Santos        bia@aluno.om.br        aluno1234  (resp: Fernanda)
  Aluno      Lucas Pereira         lucas@aluno.om.br      aluno2345  (resp: Fernanda)
  Aluno      Camila Rocha          camila@aluno.om.br     aluno3456  (resp: Ricardo)
  Aluno      Diego Alves           diego@aluno.om.br      aluno4567  (resp: Ricardo)
  Aluno      Julio Cesar           czar@aluno.om.br       aluno0000  (resp: Phyllipe)

Uso:
    python scripts/manutencao/reset_cenario.py
    python scripts/manutencao/reset_cenario.py --confirmar
"""

import sys, os
from datetime import date
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models import TipoPessoa, Usuario, Professor, Aluno
from sqlalchemy import text

app = create_app()

ADMIN = {
    "nome":       "Professor Phyllipe",
    "email":      "phyllipe@om.edu.br",
    "senha":      "prof0000",
    "nascimento": date(1986, 3, 12),
}

PROFESSORES = [
    {
        "nome":       "Fernanda Oliveira",
        "email":      "fernanda@om.edu.br",
        "senha":      "prof1234",
        "nascimento": date(1985, 6, 14),
    },
    {
        "nome":       "Ricardo Mendes",
        "email":      "ricardo@om.edu.br",
        "senha":      "prof5678",
        "nascimento": date(1979, 11, 3),
    },
]

# professor_idx: 0 = Fernanda, 1 = Ricardo, 2 = Admin (Phyllipe)
ALUNOS = [
    {
        "nome":          "Beatriz Santos",
        "email":         "bia@aluno.om.br",
        "login":         "bia",
        "senha":         "aluno1234",
        "nascimento":    date(2010, 3, 22),
        "escolaridade":  "Ensino Fundamental II",
        "professor_idx": 0,
    },
    {
        "nome":          "Lucas Pereira",
        "email":         "lucas@aluno.om.br",
        "login":         "lucas",
        "senha":         "aluno2345",
        "nascimento":    date(2009, 8, 7),
        "escolaridade":  "Ensino Médio",
        "professor_idx": 0,
    },
    {
        "nome":          "Camila Rocha",
        "email":         "camila@aluno.om.br",
        "login":         "camila",
        "senha":         "aluno3456",
        "nascimento":    date(2011, 1, 15),
        "escolaridade":  "Ensino Fundamental II",
        "professor_idx": 1,
    },
    {
        "nome":          "Diego Alves",
        "email":         "diego@aluno.om.br",
        "login":         "diego",
        "senha":         "aluno4567",
        "nascimento":    date(2010, 5, 30),
        "escolaridade":  "Ensino Médio",
        "professor_idx": 1,
    },
    {
        "nome":          "Julio Cesar",
        "email":         "czar@aluno.om.br",
        "login":         "czar",
        "senha":         "aluno0000",
        "nascimento":    date(2008, 9, 10),
        "escolaridade":  "Ensino Médio",
        "professor_idx": 2,  # Admin (Phyllipe)
    },
]

def ok(msg):   print(f"  [OK] {msg}")
def skip(msg): print(f"  [--] {msg}")
def info(msg): print(f"       {msg}")


with app.app_context():

    # ── Estado atual ──────────────────────────────────────────────────────
    tabelas = [
        "comparacao", "giros", "trafego", "simulacao_trajetoria", "lateralidade",
        "log_sessao", "atividade_aluno", "atividade_mapa", "atividade",
        "mapa", "aluno", "professor", "usuario",
    ]
    print("Estado atual do banco:")
    for t in tabelas:
        count = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        if count:
            print(f"  {t}: {count}")
    print()

    # ── Confirmação ───────────────────────────────────────────────────────
    if "--confirmar" not in sys.argv:
        resp = input("Isso apaga TODOS os dados e recria apenas o cenário base. Digite 'sim' para continuar: ")
        if resp.strip().lower() != "sim":
            print("Operação cancelada.")
            sys.exit(0)

    # ── Limpeza em ordem (respeita FKs) ──────────────────────────────────
    print("\nLimpando banco...")
    for t in ["comparacao", "giros", "trafego", "simulacao_trajetoria", "lateralidade"]:
        db.session.execute(text(f'DELETE FROM "{t}"'))
    db.session.execute(text('DELETE FROM "log_sessao"'))
    db.session.execute(text('DELETE FROM "atividade_aluno"'))
    db.session.execute(text('DELETE FROM "atividade_mapa"'))
    db.session.execute(text('DELETE FROM "atividade"'))
    db.session.execute(text('DELETE FROM "mapa"'))

    alunos_usr_ids = [r[0] for r in db.session.execute(text('SELECT id_usuario FROM "aluno"')).fetchall()]
    db.session.execute(text('DELETE FROM "aluno"'))

    profs_usr_ids = [r[0] for r in db.session.execute(
        text('SELECT id_usuario FROM "professor" WHERE id_usuario != 1')
    ).fetchall()]
    db.session.execute(text('DELETE FROM "professor" WHERE id_usuario != 1'))

    ids_remover = list(set(alunos_usr_ids + profs_usr_ids))
    if ids_remover:
        placeholders = ", ".join(str(i) for i in ids_remover)
        db.session.execute(text(f'DELETE FROM "usuario" WHERE id_usuario IN ({placeholders})'))

    db.session.commit()
    ok("Banco limpo.")

    # ── Atualizar admin (id_usuario = 1) ──────────────────────────────────
    print("\nAtualizando admin...")
    admin_usr = Usuario.query.get(1)
    if admin_usr:
        admin_usr.nome_completo = ADMIN["nome"]
        admin_usr.email         = ADMIN["email"]
        admin_usr.senha_hash    = generate_password_hash(ADMIN["senha"])
        admin_usr.data_nascimento = ADMIN["nascimento"]
        db.session.commit()
        ok(f"Admin atualizado: {ADMIN['nome']} <{ADMIN['email']}>")
    else:
        print("  [ERRO] Usuário admin (id=1) não encontrado. Execute init_db.py primeiro.")
        sys.exit(1)

    admin_prof = Professor.query.filter_by(id_usuario=1).first()
    if not admin_prof:
        admin_prof = Professor(id_usuario=1)
        db.session.add(admin_prof)
        db.session.commit()
        ok("Registro Professor criado para admin.")

    # ── Criar professores ─────────────────────────────────────────────────
    print("\nCriando professores...")
    tipo_prof  = TipoPessoa.query.filter_by(descricao="Professor").first()
    tipo_aluno = TipoPessoa.query.filter_by(descricao="Aluno").first()

    prof_objs = [admin_prof]  # índice 2 = admin
    for p in PROFESSORES:
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
        prof = Professor(id_usuario=usr.id_usuario)
        db.session.add(prof)
        db.session.flush()
        prof_objs.insert(len(prof_objs) - 1, prof)  # insere antes do admin
        ok(f"Professor: {p['nome']} <{p['email']}>")

    db.session.commit()

    # prof_objs[0] = Fernanda, prof_objs[1] = Ricardo, prof_objs[2] = Admin (Phyllipe)
    # ── Criar alunos ──────────────────────────────────────────────────────
    print("\nCriando alunos...")
    for a in ALUNOS:
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

        prof_responsavel = prof_objs[a["professor_idx"]]
        aluno = Aluno(
            id_usuario=usr.id_usuario,
            id_professor_responsavel=prof_responsavel.id_professor,
            escolaridade=a["escolaridade"],
            login=a["login"],
        )
        db.session.add(aluno)

        resp_nome = PROFESSORES[a["professor_idx"]]["nome"] if a["professor_idx"] < 2 else ADMIN["nome"]
        ok(f"Aluno: {a['nome']} <{a['email']}> -> {resp_nome}")

    db.session.commit()

    # ── Tabela final ──────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print(f"{'Perfil':<10} {'Nome':<22} {'E-mail':<30} {'Senha'}")
    print("-" * 72)
    print(f"{'Admin':<10} {ADMIN['nome']:<22} {ADMIN['email']:<30} {ADMIN['senha']}")
    for p in PROFESSORES:
        print(f"{'Professor':<10} {p['nome']:<22} {p['email']:<30} {p['senha']}")
    print("-" * 72)
    for a in ALUNOS:
        resp = PROFESSORES[a["professor_idx"]]["nome"].split()[0] if a["professor_idx"] < 2 else "Phyllipe"
        print(f"{'Aluno':<10} {a['nome']:<22} {a['email']:<30} {a['senha']}  (resp: {resp})")
    print("=" * 72)
    print("\nCenário recriado com sucesso.")
