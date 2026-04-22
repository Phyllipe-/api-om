"""
seed_atividade_iv.py
=====================
Insere dados simulados para o professor phyllipe@unilab.edu.br:

  1. Novo aluno: Lucas Oliveira
  2. Atividade IV  com mapa 'Quarto 0' (id_mapa = 13)
  3. Vincula todos os alunos do professor (existentes + novo) à atividade
  4. Gera 5 sessões simuladas por aluno com dados_log realistas

Uso:
    cd dashboard/api-om
    python scripts/demo/seed_atividade_iv.py
"""

import sys, os, json, random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import (
    TipoPessoa, Usuario, Professor, Aluno,
    Mapa, LogSessao, Atividade, AtividadeMapa, AtividadeAluno,
    Lateralidade, SimulacaoTrajetoria, Trafego, Giros, Comparacao,
)

# ── Configuração ──────────────────────────────────────────────────────────────
PROF_EMAIL  = "phyllipe@unilab.edu.br"
NOME_ATIV   = "Atividade IV"
NOME_MAPA   = "Quarto 0"
N_SESSOES   = 5

NOVO_ALUNO = {
    "nome":        "Lucas Oliveira",
    "email":       "lucas.oliveira@aluno.edu.br",
    "login":       "lucas.oliveira",
    "nascimento":  date(2007, 4, 22),
    "escolaridade":"Ensino Médio",
    # perfil de desempenho
    "base_precisao":  55,
    "base_objetivos": 60,
    "base_fluidez":   50,
    "tendencia":      "melhora",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, round(v)))

def gerar_metricas(base_p, base_o, base_f, idx, tendencia):
    ganho = (idx * 4) if tendencia == "melhora" else 0
    ruido = random.uniform(-8, 8)
    return (
        clamp(base_p + ganho + ruido),
        clamp(base_o + ganho + ruido * 0.8),
        clamp(base_f + ganho + ruido * 1.2),
    )

def gerar_turn_sequence(pos, direction, n):
    """Gera n ações de giro consecutivas na mesma posição e direção."""
    return [
        {
            "actionType": 1,
            "direction":  direction,
            "position":   {"x": pos[0], "y": 0.0, "z": pos[1]},
            "timestamp":  round(random.uniform(5, 60), 2),
        }
        for _ in range(n)
    ]

def gerar_movement_action(pos, direction):
    return {
        "actionType": 0,
        "direction":  direction,
        "position":   {"x": pos[0], "y": 0.0, "z": pos[1]},
        "timestamp":  round(random.uniform(1, 60), 2),
    }

def gerar_collision(pos):
    return {
        "position":  {"x": pos[0], "y": 0.0, "z": pos[1]},
        "timestamp": round(random.uniform(1, 60), 2),
    }

def gerar_dados_log(id_aluno, id_mapa, precisao, objetivos, fluidez):
    """
    Gera o JSONB dados_log com estrutura realista usada pelos gráficos:
      - objectives[].actions  → lateralidade + giros
      - objectives[].collisions → tráfego de colisões
      - objectives[].endTime  → objetivo concluído
      - results.clearedMap / totalSessionTime
    """
    n_objetivos = random.randint(3, 6)
    n_concluidos = clamp(round(n_objetivos * objetivos / 100), 0, n_objetivos)
    n_colisoes_total = clamp(round((1 - precisao / 100) * 20), 0, 20)

    objectives = []
    for i in range(n_objetivos):
        actions   = []
        colisoes  = []
        concluido = i < n_concluidos

        # Posição aleatória dentro de um quarto ~8×8 tiles
        pos = (round(random.uniform(1, 7), 1), round(random.uniform(1, 7), 1))

        # Movimentos laterais (lateralidade)
        n_mov = random.randint(10, 30)
        for _ in range(n_mov):
            d = random.choice([0, 4])  # 0=esq, 4=dir
            actions.append(gerar_movement_action(pos, d))

        # Giros — mistura de 90°/180°/270°/360°
        n_giros = random.randint(2, 8)
        tipos_giro = [1, 2, 3, 4]  # n de turnos consecutivos
        for _ in range(n_giros):
            n_turns = random.choice(tipos_giro)
            dir_giro = random.choice([0, 4])
            # Posição fixa para que o detector agrupe corretamente
            giro_pos = (round(random.uniform(1, 7), 1), round(random.uniform(1, 7), 1))
            actions.extend(gerar_turn_sequence(giro_pos, dir_giro, n_turns))
            # Intercala movimento após giro
            actions.append(gerar_movement_action(pos, random.choice([0, 4])))

        # Colisões distribuídas nos objetivos
        n_col_obj = round(n_colisoes_total / n_objetivos) if i < n_objetivos - 1 \
                    else max(0, n_colisoes_total - round(n_colisoes_total / n_objetivos) * (n_objetivos - 1))
        for _ in range(n_col_obj):
            colisoes.append(gerar_collision(pos))

        objectives.append({
            "actions":    actions,
            "collisions": colisoes,
            "endTime":    round(random.uniform(20, 90), 1) if concluido else 0,
        })

    # Duração total
    dist_otima      = round(random.uniform(10, 30), 2)
    dist_percorrida = round(dist_otima / max(fluidez / 100, 0.05), 2)
    duracao         = round(dist_percorrida / 0.8 + random.uniform(-5, 15))
    cleared         = n_concluidos == n_objetivos

    return {
        "id_aluno":   id_aluno,
        "id_mapa":    id_mapa,
        "objectives": objectives,
        "results": {
            "clearedMap":       cleared,
            "totalSessionTime": max(30, duracao),
        },
    }

def salvar_json(pasta_base, subpasta, nome, conteudo):
    pasta = os.path.join(pasta_base, subpasta)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=2)
    return f"/{subpasta}/{nome}"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = create_app()
    uploads = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "uploads")

    with app.app_context():

        # ── Professor ─────────────────────────────────────────────────────
        usr_prof = Usuario.query.filter_by(email=PROF_EMAIL).first()
        if not usr_prof:
            print(f"ERRO: professor {PROF_EMAIL} não encontrado.")
            sys.exit(1)
        prof = Professor.query.filter_by(id_usuario=usr_prof.id_usuario).first()
        print(f"Professor: {usr_prof.nome_completo} (id_professor={prof.id_professor})")

        # ── Mapa ──────────────────────────────────────────────────────────
        mapa = Mapa.query.filter_by(nome_mapa=NOME_MAPA).first()
        if not mapa:
            print(f"ERRO: mapa '{NOME_MAPA}' não encontrado no banco.")
            sys.exit(1)
        print(f"Mapa: {mapa.nome_mapa} (id_mapa={mapa.id_mapa})")

        # ── Novo aluno ────────────────────────────────────────────────────
        tipo_aluno = TipoPessoa.query.filter_by(descricao="Aluno").first()
        aluno_novo = Aluno.query.join(Usuario).filter(
            Usuario.email == NOVO_ALUNO["email"]
        ).first()

        if not aluno_novo:
            u = Usuario(
                id_tipo=tipo_aluno.id_tipo,
                nome_completo=NOVO_ALUNO["nome"],
                data_nascimento=NOVO_ALUNO["nascimento"],
                email=NOVO_ALUNO["email"],
                senha_hash=generate_password_hash("aluno123"),
            )
            db.session.add(u)
            db.session.flush()
            aluno_novo = Aluno(
                id_usuario=u.id_usuario,
                id_professor_responsavel=prof.id_professor,
                escolaridade=NOVO_ALUNO["escolaridade"],
                login=NOVO_ALUNO["login"],
            )
            db.session.add(aluno_novo)
            db.session.flush()
            db.session.commit()
            print(f"  ✓ Novo aluno criado: {NOVO_ALUNO['nome']} (id_aluno={aluno_novo.id_aluno})")
        else:
            print(f"  · Aluno já existe: {NOVO_ALUNO['nome']} (id_aluno={aluno_novo.id_aluno})")

        # ── Todos os alunos do professor ──────────────────────────────────
        todos_alunos_db = Aluno.query.filter_by(
            id_professor_responsavel=prof.id_professor
        ).all()

        alunos_info = []
        for a in todos_alunos_db:
            au = Usuario.query.get(a.id_usuario)
            if a.id_aluno == aluno_novo.id_aluno:
                cfg = NOVO_ALUNO
            else:
                cfg = {
                    "base_precisao":  random.randint(40, 75),
                    "base_objetivos": random.randint(45, 80),
                    "base_fluidez":   random.randint(35, 70),
                    "tendencia":      random.choice(["melhora", "estavel"]),
                }
            alunos_info.append((a, au, cfg))
            print(f"  · Aluno: {au.nome_completo} (id_aluno={a.id_aluno})")

        # ── Atividade IV ──────────────────────────────────────────────────
        ativ = Atividade.query.filter_by(
            nome=NOME_ATIV,
            id_professor=prof.id_professor
        ).first()

        if not ativ:
            ativ = Atividade(
                nome=NOME_ATIV,
                descricao="Navegação no Quarto 0 — quarto nível de atividade.",
                id_professor=prof.id_professor,
            )
            db.session.add(ativ)
            db.session.flush()
            db.session.add(AtividadeMapa(
                id_atividade=ativ.id_atividade,
                id_mapa=mapa.id_mapa,
                ordem=1,
            ))
            db.session.commit()
            print(f"  ✓ Atividade criada: {NOME_ATIV} (id={ativ.id_atividade})")
        else:
            print(f"  · Atividade já existe: {NOME_ATIV} (id={ativ.id_atividade})")

        # ── Vincular alunos à atividade ───────────────────────────────────
        for (aluno_obj, _, __) in alunos_info:
            if not AtividadeAluno.query.filter_by(
                id_atividade=ativ.id_atividade,
                id_aluno=aluno_obj.id_aluno,
            ).first():
                db.session.add(AtividadeAluno(
                    id_atividade=ativ.id_atividade,
                    id_aluno=aluno_obj.id_aluno,
                ))
        db.session.commit()
        print(f"  ✓ Alunos vinculados à atividade")

        # ── Sessões + análises por aluno ──────────────────────────────────
        for (aluno_obj, usr_aluno, cfg) in alunos_info:
            print(f"\n  Gerando sessões para {usr_aluno.nome_completo}…")

            for s in range(N_SESSOES):
                data_sessao = datetime.utcnow() - timedelta(weeks=(N_SESSOES - 1 - s))
                precisao, objetivos, fluidez = gerar_metricas(
                    cfg["base_precisao"], cfg["base_objetivos"], cfg["base_fluidez"],
                    s, cfg["tendencia"],
                )

                dados_log = gerar_dados_log(
                    aluno_obj.id_aluno, mapa.id_mapa, precisao, objetivos, fluidez
                )

                log_nome = (
                    f"log_{aluno_obj.id_aluno}_{mapa.id_mapa}"
                    f"_{data_sessao.strftime('%Y%m%d%H%M%S')}.json"
                )

                sessao = LogSessao(
                    id_aluno=aluno_obj.id_aluno,
                    id_criador=prof.id_professor,
                    id_mapa=mapa.id_mapa,
                    id_atividade=ativ.id_atividade,
                    caminho_arquivo_log=f"/sessoes/{log_nome}",
                    dados_log=dados_log,
                    data_criacao_arquivo_log=data_sessao,
                )
                db.session.add(sessao)
                db.session.flush()

                dados_log["id_log"] = sessao.id_log
                salvar_json(uploads, "sessoes", log_nome, dados_log)

                # Análise: apenas marcadores de caminho (dados reais já no dados_log)
                for tipo, Modelo in [
                    ("lateralidade",         Lateralidade),
                    ("simulacao_trajetoria", SimulacaoTrajetoria),
                    ("trafego",              Trafego),
                    ("giros",                Giros),
                    ("comparacao",           Comparacao),
                ]:
                    if Modelo.query.filter_by(id_log=sessao.id_log).first():
                        continue
                    nome_json = f"{tipo}_{sessao.id_log}.json"
                    caminho   = salvar_json(uploads, "analises", nome_json,
                                           {"id_log": sessao.id_log, "tipo": tipo})
                    db.session.add(Modelo(id_log=sessao.id_log,
                                         caminho_arquivo_json=caminho))

                db.session.commit()
                cleared = dados_log["results"]["clearedMap"]
                print(f"    sessão {s+1}/{N_SESSOES}  precisão={precisao}%  "
                      f"obj={objetivos}%  fluidez={fluidez}%  "
                      f"{'✓ concluída' if cleared else '○ não concluída'}")

        # ── Resumo ────────────────────────────────────────────────────────
        print("\n" + "─" * 50)
        print(f"Atividade IV  : id={ativ.id_atividade}")
        print(f"Mapa          : {mapa.nome_mapa} (id={mapa.id_mapa})")
        print(f"Alunos        : {len(alunos_info)}")
        print(f"Sessões       : {N_SESSOES} por aluno = {N_SESSOES * len(alunos_info)} total")
        print("─" * 50)
        print("Seed concluído.")

if __name__ == "__main__":
    random.seed()
    main()
