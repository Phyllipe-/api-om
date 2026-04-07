"""
seed_demo.py — Roteiro de geração de dados de demonstração
===========================================================

Popula o banco com:
  - 1 professor administrador
  - 2 professores adicionais
  - 8 alunos distribuídos entre os professores
  - 5 mapas variados
  - 2 atividades com mapas atribuídos
  - 5 sessões por aluno (últimas 5 semanas)
  - JSONs de análise com métricas reais para cada sessão:
      · Precisão  — baseada em colisões (0–100%)
      · Objetivos — metas alcançadas / metas totais (0–100%)
      · Fluidez   — distância ótima / distância percorrida (0–100%)

Uso:
    cd dashboard/api-om
    python scripts/seed_demo.py [--limpar]

Flags:
    --limpar    Apaga todos os dados de análise/sessão/aluno antes de inserir.
                Mantém tipos de pessoa e professor admin (id=1).
"""

import sys
import os
import json
import math
import random
import argparse
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import (
    TipoPessoa, Usuario, Professor, Aluno,
    Mapa, LogSessao, Atividade, AtividadeMapa, AtividadeAluno,
    Lateralidade, SimulacaoTrajetoria, Trafego, Giros, Comparacao
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuração dos perfis de aluno
# Cada perfil define a tendência das 3 métricas ao longo das sessões.
# Os valores são a média esperada (0–100) com variação aleatória de ±10.
# ─────────────────────────────────────────────────────────────────────────────
PERFIS_ALUNO = [
    # nome               escolaridade              precisao  objetivos  fluidez  tendencia
    ("Bosco Lima",       "Ensino Fundamental II",  25,       35,        18,      "estavel"),
    ("Carlos Souza",     "Ensino Médio",            15,       45,        22,      "melhora"),
    ("Francisco Neto",   "Ensino Fundamental I",   40,       50,        42,      "melhora"),
    ("Mariana Costa",    "Ensino Superior",         28,       30,        35,      "estavel"),
    ("Ana Paula",        "Ensino Médio",            70,       80,        72,      "melhora"),
    ("Roberto Dias",     "Ensino Fundamental II",  55,       60,        50,      "estavel"),
    ("Juliana Ramos",    "Ensino Fundamental I",   10,       20,        12,      "melhora"),
    ("Pedro Alves",      "Ensino Superior",         80,       90,        85,      "estavel"),
]

MAPAS = [
    ("Casa Nível 1",    "/mapas/casa_nivel1.xml"),
    ("Casa Nível 2",    "/mapas/casa_nivel2.xml"),
    ("Escola",          "/mapas/escola.xml"),
    ("Corredor",        "/mapas/corredor.xml"),
    ("Supermercado",    "/mapas/supermercado.xml"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Funções de geração de métricas
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, round(v)))

def gerar_metricas(base_precisao, base_objetivos, base_fluidez, sessao_idx, tendencia):
    """
    Gera os 3 valores de métrica para a sessão `sessao_idx` (0=mais antiga).
    Tendência 'melhora': incremento gradual ao longo das sessões.
    Tendência 'estavel': variação aleatória em torno da base.
    """
    ganho = (sessao_idx * 4) if tendencia == "melhora" else 0
    ruido = random.uniform(-8, 8)

    precisao  = _clamp(base_precisao  + ganho + ruido)
    objetivos = _clamp(base_objetivos + ganho + ruido * 0.8)
    fluidez   = _clamp(base_fluidez   + ganho + ruido * 1.2)
    return precisao, objetivos, fluidez

def gerar_log_sessao(id_log, id_aluno, id_mapa, precisao, objetivos, fluidez, data_sessao):
    """
    Gera o conteúdo do JSON de log de uma sessão.

    Estrutura baseada nas 3 métricas:
      - colisoes         → alimenta Precisão
      - objetivos_total / objetivos_alcancados → alimenta Objetivos
      - distancia_otima / distancia_percorrida  → alimenta Fluidez
      - posicoes         → lista de pontos XZ (trajetória real)
    """
    obj_total = random.randint(3, 8)
    obj_alc   = _clamp(round(obj_total * objetivos / 100), 0, obj_total)

    # Colisões: Precisão 100% = 0 colisões; Precisão 0% = 30 colisões
    colisoes = _clamp(round((1 - precisao / 100) * 30), 0, 30)

    # Distâncias: Fluidez = otima/percorrida → percorrida = otima / fluidez
    dist_otima      = round(random.uniform(15.0, 45.0), 2)
    dist_percorrida = round(dist_otima / max(fluidez / 100, 0.05), 2)

    # Trajetória simulada: série de pontos XZ
    n_pontos = random.randint(40, 120)
    posicoes = []
    x, z = 0.0, 0.0
    for i in range(n_pontos):
        x += random.uniform(-0.5, 0.8)
        z += random.uniform(-0.3, 0.9)
        posicoes.append({"x": round(x, 2), "z": round(z, 2), "t": i * 0.5})

    # Duracao em segundos
    duracao = round(dist_percorrida / 0.8 + random.uniform(-10, 20))

    return {
        "id_log": id_log,
        "id_aluno": id_aluno,
        "id_mapa": id_mapa,
        "data": data_sessao.isoformat(),
        "duracao_segundos": max(30, duracao),
        "colisoes": colisoes,
        "objetivos_total": obj_total,
        "objetivos_alcancados": obj_alc,
        "atividade_finalizada": obj_alc == obj_total,
        "distancia_otima": dist_otima,
        "distancia_percorrida": dist_percorrida,
        "fluidez_pct": round(dist_otima / dist_percorrida * 100, 1),
        "precisao_pct": precisao,
        "objetivos_pct": round(obj_alc / obj_total * 100, 1),
        "posicoes": posicoes,
    }

def gerar_analise_json(tipo, id_log, metricas_log):
    """
    Gera o JSON específico de cada tipo de análise,
    usando os dados do log como fonte de verdade.
    """
    base = {
        "id_log": id_log,
        "tipo": tipo,
        "gerado_em": datetime.utcnow().isoformat(),
    }

    if tipo == "lateralidade":
        # Deriva desvios laterais da trajetória
        n = random.randint(10, 30)
        return {**base,
            "desvios_esquerda": round(n * random.uniform(0.3, 0.7)),
            "desvios_direita":  round(n * random.uniform(0.3, 0.7)),
            "desvio_medio_graus": round(random.uniform(5, 35), 1),
            "colisoes": metricas_log["colisoes"],
            "precisao_pct": metricas_log["precisao_pct"],
        }

    if tipo == "simulacao_trajetoria":
        return {**base,
            "distancia_otima": metricas_log["distancia_otima"],
            "distancia_percorrida": metricas_log["distancia_percorrida"],
            "fluidez_pct": metricas_log["fluidez_pct"],
            "n_pontos": len(metricas_log["posicoes"]),
            "posicoes": metricas_log["posicoes"][:20],  # amostra
        }

    if tipo == "trafego":
        # Mapa de calor: células de 1m² com contagem de passagens
        celulas = []
        for _ in range(random.randint(15, 40)):
            celulas.append({
                "x": round(random.uniform(0, 10), 1),
                "z": round(random.uniform(0, 10), 1),
                "passagens": random.randint(1, 8),
            })
        return {**base, "celulas": celulas,
                "duracao_segundos": metricas_log["duracao_segundos"]}

    if tipo == "giros":
        n_giros = random.randint(4, 20)
        return {**base,
            "total_giros": n_giros,
            "giros_esquerda":  round(n_giros * random.uniform(0.3, 0.7)),
            "giros_direita":   round(n_giros * random.uniform(0.3, 0.7)),
            "angulo_medio": round(random.uniform(45, 180), 1),
        }

    if tipo == "comparacao":
        # Comparação com sessão anterior (simplificada)
        delta_p = round(random.uniform(-15, 20), 1)
        delta_o = round(random.uniform(-10, 15), 1)
        delta_f = round(random.uniform(-12, 18), 1)
        return {**base,
            "delta_precisao_pct":  delta_p,
            "delta_objetivos_pct": delta_o,
            "delta_fluidez_pct":   delta_f,
            "evolucao": "melhora" if (delta_p + delta_o + delta_f) > 0 else "regressao",
        }

    return base

# ─────────────────────────────────────────────────────────────────────────────
# Persistência dos arquivos JSON de análise
# ─────────────────────────────────────────────────────────────────────────────

def salvar_json(pasta_base, subpasta, nome, conteudo):
    pasta = os.path.join(pasta_base, subpasta)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=2)
    # Retorna o caminho relativo usado como referência na API
    return f"/{subpasta}/{nome}"

# ─────────────────────────────────────────────────────────────────────────────
# Script principal
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed de dados de demonstração para api-om")
    parser.add_argument("--limpar", action="store_true",
                        help="Remove dados existentes antes de inserir")
    args = parser.parse_args()

    app = create_app()
    uploads = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")

    with app.app_context():

        # ── Limpar dados anteriores ───────────────────────────────────────
        if args.limpar:
            print("Limpando dados anteriores…")
            for Model in [Comparacao, Giros, Trafego, SimulacaoTrajetoria, Lateralidade,
                          AtividadeAluno, AtividadeMapa, Atividade,
                          LogSessao, Aluno, Mapa]:
                db.session.query(Model).delete()
            # Remove usuários que não são o admin (id_usuario != 1)
            db.session.query(Professor).filter(Professor.id_usuario != 1).delete()
            db.session.query(Usuario).filter(
                Usuario.id_usuario != 1,
                Usuario.id_tipo == (db.session.query(TipoPessoa)
                                    .filter_by(descricao="Aluno").first() or
                                    type('T', (), {'id_tipo': -1})()).id_tipo
            ).delete()
            db.session.commit()
            print("  ✓ Dados limpos.")

        # ── Tipos de pessoa ───────────────────────────────────────────────
        tipo_prof  = TipoPessoa.query.filter_by(descricao="Professor").first()
        tipo_aluno = TipoPessoa.query.filter_by(descricao="Aluno").first()
        if not tipo_prof or not tipo_aluno:
            print("ERRO: Tipos de pessoa não encontrados. Execute init_db.py primeiro.")
            sys.exit(1)

        # ── Professor admin (id=1 — apenas garante existência) ───────────
        admin_usr = Usuario.query.get(1)
        if not admin_usr:
            admin_usr = Usuario(
                id_tipo=tipo_prof.id_tipo,
                nome_completo="Professor Admin",
                data_nascimento=date(1980, 1, 1),
                email="admin@om.edu.br",
                senha_hash=generate_password_hash("admin123"),
            )
            db.session.add(admin_usr)
            db.session.flush()
            db.session.add(Professor(id_usuario=admin_usr.id_usuario,
                                     registro_profissional="OM-ADM-001"))
            db.session.commit()
            print(f"  ✓ Admin criado: {admin_usr.email}")

        admin_prof = Professor.query.filter_by(id_usuario=admin_usr.id_usuario).first()

        # ── Professores adicionais ────────────────────────────────────────
        profs_extra = [
            ("Ana Beatriz Ferreira", "1985-06-12", "ana.ferreira@om.edu.br",  "CREFITO-3/10001-F"),
            ("Carlos Eduardo Lima",  "1979-03-28", "carlos.lima@om.edu.br",   "CREFITO-3/10002-F"),
        ]
        professores = [admin_prof]
        for nome, nasc, email, reg in profs_extra:
            if not Usuario.query.filter_by(email=email).first():
                u = Usuario(id_tipo=tipo_prof.id_tipo, nome_completo=nome,
                            data_nascimento=datetime.strptime(nasc, "%Y-%m-%d").date(),
                            email=email, senha_hash=generate_password_hash("prof123"))
                db.session.add(u); db.session.flush()
                p = Professor(id_usuario=u.id_usuario, registro_profissional=reg)
                db.session.add(p); db.session.flush()
                professores.append(p)
                print(f"  ✓ Professor criado: {email}")
            else:
                professores.append(Professor.query.join(Usuario).filter(
                    Usuario.email == email).first())

        db.session.commit()

        # ── Mapas ─────────────────────────────────────────────────────────
        mapas = []
        for nome, caminho in MAPAS:
            m = Mapa.query.filter_by(nome_mapa=nome).first()
            if not m:
                m = Mapa(nome_mapa=nome, id_criador=admin_prof.id_professor,
                         caminho_arquivo_xml=caminho)
                db.session.add(m); db.session.flush()
                print(f"  ✓ Mapa criado: {nome}")
            mapas.append(m)
        db.session.commit()

        # ── Atividades ────────────────────────────────────────────────────
        ativ1 = Atividade.query.filter_by(nome="Percurso Básico").first()
        if not ativ1:
            ativ1 = Atividade(nome="Percurso Básico",
                              descricao="Introdução ao ambiente doméstico.",
                              id_professor=admin_prof.id_professor)
            db.session.add(ativ1); db.session.flush()
            db.session.add_all([
                AtividadeMapa(id_atividade=ativ1.id_atividade, id_mapa=mapas[0].id_mapa, ordem=1),
                AtividadeMapa(id_atividade=ativ1.id_atividade, id_mapa=mapas[3].id_mapa, ordem=2),
            ])
            print("  ✓ Atividade criada: Percurso Básico")

        ativ2 = Atividade.query.filter_by(nome="Percurso Avançado").first()
        if not ativ2:
            ativ2 = Atividade(nome="Percurso Avançado",
                              descricao="Ambientes complexos: escola e supermercado.",
                              id_professor=admin_prof.id_professor)
            db.session.add(ativ2); db.session.flush()
            db.session.add_all([
                AtividadeMapa(id_atividade=ativ2.id_atividade, id_mapa=mapas[2].id_mapa, ordem=1),
                AtividadeMapa(id_atividade=ativ2.id_atividade, id_mapa=mapas[4].id_mapa, ordem=2),
            ])
            print("  ✓ Atividade criada: Percurso Avançado")

        db.session.commit()

        # ── Alunos + Sessões + Análises ───────────────────────────────────
        N_SESSOES = 5  # sessões por aluno (1 por semana, das últimas 5)

        for idx, (nome, escolaridade, base_p, base_o, base_f, tendencia) in enumerate(PERFIS_ALUNO):
            email = f"{nome.split()[0].lower()}.{nome.split()[-1].lower()}@aluno.om.br"
            login = f"{nome.split()[0].lower()}.{nome.split()[-1].lower()}"

            # Distribui alunos entre professores
            prof = professores[idx % len(professores)]

            aluno_obj = Aluno.query.join(Usuario).filter(Usuario.email == email).first()
            if not aluno_obj:
                u = Usuario(
                    id_tipo=tipo_aluno.id_tipo,
                    nome_completo=nome,
                    data_nascimento=date(2008 - idx, (idx % 12) + 1, 10 + idx),
                    email=email,
                    senha_hash=generate_password_hash("aluno123"),
                )
                db.session.add(u); db.session.flush()
                aluno_obj = Aluno(
                    id_usuario=u.id_usuario,
                    id_professor_responsavel=prof.id_professor,
                    escolaridade=escolaridade,
                    login=login,
                )
                db.session.add(aluno_obj); db.session.flush()
                print(f"  ✓ Aluno criado: {nome} → prof {prof.id_professor}")

            # Vincula aluno à atividade correspondente
            ativ = ativ2 if idx >= 4 else ativ1
            if not AtividadeAluno.query.filter_by(
                    id_atividade=ativ.id_atividade,
                    id_aluno=aluno_obj.id_aluno).first():
                db.session.add(AtividadeAluno(
                    id_atividade=ativ.id_atividade,
                    id_aluno=aluno_obj.id_aluno))

            # Sessões semanais
            for s in range(N_SESSOES):
                data_sessao = datetime.utcnow() - timedelta(weeks=(N_SESSOES - 1 - s))
                mapa_sessao = mapas[s % len(mapas)]

                precisao, objetivos, fluidez = gerar_metricas(
                    base_p, base_o, base_f, s, tendencia)

                # Log da sessão
                log_nome = f"log_{aluno_obj.id_aluno}_{mapa_sessao.id_mapa}_{data_sessao.strftime('%Y%m%d')}.json"
                metricas_log = gerar_log_sessao(
                    id_log=None,  # preenchido após flush
                    id_aluno=aluno_obj.id_aluno,
                    id_mapa=mapa_sessao.id_mapa,
                    precisao=precisao,
                    objetivos=objetivos,
                    fluidez=fluidez,
                    data_sessao=data_sessao,
                )

                sessao = LogSessao(
                    id_aluno=aluno_obj.id_aluno,
                    id_criador=prof.id_professor,
                    id_mapa=mapa_sessao.id_mapa,
                    caminho_arquivo_log=f"/sessoes/{log_nome}",
                    data_criacao_arquivo_log=data_sessao,
                )
                db.session.add(sessao); db.session.flush()

                # Salva log no disco
                metricas_log["id_log"] = sessao.id_log
                salvar_json(uploads, "sessoes", log_nome, metricas_log)

                # Análises para cada sessão
                tipos_analise = {
                    "lateralidade":         Lateralidade,
                    "simulacao_trajetoria": SimulacaoTrajetoria,
                    "trafego":              Trafego,
                    "giros":                Giros,
                    "comparacao":           Comparacao,
                }
                for tipo, Modelo in tipos_analise.items():
                    if Modelo.query.filter_by(id_log=sessao.id_log).first():
                        continue
                    conteudo = gerar_analise_json(tipo, sessao.id_log, metricas_log)
                    nome_json = f"{tipo}_{sessao.id_log}.json"
                    caminho   = salvar_json(uploads, "analises", nome_json, conteudo)
                    db.session.add(Modelo(id_log=sessao.id_log,
                                          caminho_arquivo_json=caminho))

            db.session.commit()
            print(f"    → {N_SESSOES} sessões + análises geradas para {nome}")

        # ── Resumo final ──────────────────────────────────────────────────
        print("\n" + "─" * 50)
        print(f"Professores : {Professor.query.count()}")
        print(f"Alunos      : {Aluno.query.count()}")
        print(f"Mapas       : {Mapa.query.count()}")
        print(f"Sessões     : {LogSessao.query.count()}")
        print(f"Análises    : {Lateralidade.query.count()} × 5 tipos")
        print("─" * 50)
        print("Seed concluído.")

if __name__ == "__main__":
    random.seed(42)  # reproduzível
    main()
