from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import json, os
from app import db
from app.models import Professor, TipoPessoa, LogSessao, Lateralidade, SimulacaoTrajetoria, Trafego, Giros, Comparacao, Aluno

analises_bp = Blueprint('analises', __name__)

# Dicionário mágico para mapear o texto do URL para a Classe do Banco de Dados
MAPA_MODELOS_ANALISE = {
    'lateralidade': Lateralidade,
    'simulacao_trajetoria': SimulacaoTrajetoria,
    'trafego': Trafego,
    'giros': Giros,
    'comparacao': Comparacao
}

# ==========================================
# ROTA 1: REGISTAR UMA ANÁLISE (Dinâmica)
# Ex: POST /api/analises/giros
# ==========================================
@analises_bp.route('/<tipo_analise>', methods=['POST'])
@jwt_required()
def registar_analise(tipo_analise):
    # 1. Valida se o tipo de análise existe no nosso sistema
    if tipo_analise not in MAPA_MODELOS_ANALISE:
        return jsonify({"erro": f"Tipo de análise '{tipo_analise}' inválido. Use: {list(MAPA_MODELOS_ANALISE.keys())}"}), 400

    id_usuario_logado = get_jwt_identity()
    claims = get_jwt()
    
    # 2. Segurança: Apenas Professores
    tipo_aluno = TipoPessoa.query.filter_by(descricao="Aluno").first()
    if claims.get('id_tipo') == tipo_aluno.id_tipo:
        return jsonify({"erro": "Apenas professores podem registar análises."}), 403

    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    
    dados = request.get_json()
    if 'id_log' not in dados or 'caminho_arquivo_json' not in dados:
        return jsonify({"erro": "Os campos 'id_log' e 'caminho_arquivo_json' são obrigatórios."}), 400

    # 3. Segurança: O LogSessao existe e pertence a este professor?
    sessao = LogSessao.query.filter_by(id_log=dados['id_log']).first()
    if not sessao:
        return jsonify({"erro": "Sessão de treino (id_log) não encontrada."}), 404
    if sessao.id_criador != professor.id_professor:
        return jsonify({"erro": "Você não tem permissão para adicionar análises a esta sessão."}), 403

    # 4. Verifica se já existe uma análise desse tipo para esta sessão (é Unique!)
    ModeloClasse = MAPA_MODELOS_ANALISE[tipo_analise]
    analise_existente = ModeloClasse.query.filter_by(id_log=sessao.id_log).first()
    if analise_existente:
        return jsonify({"erro": f"Já existe uma análise de '{tipo_analise}' para esta sessão."}), 409

    try:
        # 5. Salva a nova análise dinamicamente
        nova_analise = ModeloClasse(
            id_log=sessao.id_log,
            caminho_arquivo_json=dados['caminho_arquivo_json']
        )
        db.session.add(nova_analise)
        db.session.commit()

        # Pega o ID gerado de forma dinâmica (como id_giros, id_lateralidade...)
        id_gerado = getattr(nova_analise, f'id_{tipo_analise.split("_")[0]}', "Registado")

        return jsonify({
            "mensagem": f"Análise de {tipo_analise} registada com sucesso!", 
            "id": id_gerado
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao registar análise: {str(e)}"}), 500


# ==========================================
# ROTA 2: BUSCAR TODAS AS ANÁLISES DE UMA SESSÃO
# Ex: GET /api/analises/sessao/1
# ==========================================
@analises_bp.route('/sessao/<int:id_log>', methods=['GET'])
@jwt_required()
def buscar_analises_da_sessao(id_log):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()

    sessao = LogSessao.query.filter_by(id_log=id_log).first()
    if not sessao:
        return jsonify({"erro": "Sessão de treino não encontrada."}), 404
        
    if professor and sessao.id_criador != professor.id_professor:
        return jsonify({"erro": "Acesso negado a esta sessão."}), 403

    # Busca os caminhos em todas as tabelas
    resultados = {}
    for nome_tipo, ModeloClasse in MAPA_MODELOS_ANALISE.items():
        registro = ModeloClasse.query.filter_by(id_log=id_log).first()
        resultados[nome_tipo] = registro.caminho_arquivo_json if registro else None

    return jsonify({
        "id_log": id_log,
        "analises": resultados
    }), 200


# ==========================================
# ROTA 3: MÉTRICAS CALCULADAS DE UMA SESSÃO
# Ex: GET /api/analises/sessao/1/metricas
# Retorna Precisão, Objetivos e Fluidez prontos para o radar chart.
# ==========================================
@analises_bp.route('/sessao/<int:id_log>/metricas', methods=['GET'])
@jwt_required()
def metricas_sessao(id_log):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()

    sessao = LogSessao.query.filter_by(id_log=id_log).first()
    if not sessao:
        return jsonify({"erro": "Sessão não encontrada."}), 404
    if professor and sessao.id_criador != professor.id_professor:
        return jsonify({"erro": "Acesso negado."}), 403

    dados = sessao.dados_log
    if not dados:
        return jsonify({"erro": "Dados de sessão não disponíveis (log não processado)."}), 404

    objectives = dados.get('objectives', [])
    results    = dados.get('results', {})
    cleared    = results.get('clearedMap', False)

    # ── Precisão: 100 − proporção de colisões sobre (ações + colisões) ──────
    total_acoes     = sum(len(o.get('actions', []))    for o in objectives)
    total_colisoes  = sum(len(o.get('collisions', [])) for o in objectives)
    total_eventos   = total_acoes + total_colisoes
    precisao = round(100 * (1 - total_colisoes / total_eventos), 1) if total_eventos > 0 else 100.0

    # ── Objetivos: mapa concluído = 100; caso contrário, objetivos com endTime > 0 ──
    if cleared:
        objetivos = 100.0
    elif objectives:
        concluidos = sum(1 for o in objectives if (o.get('endTime') or 0) > 0)
        objetivos  = round(concluidos / len(objectives) * 100, 1)
    else:
        objetivos = 0.0

    # ── Fluidez: posições únicas / total de passos (evitar retrocessos) ─────
    passos = [
        (a['position']['x'], a['position']['z'])
        for o in objectives
        for a in o.get('actions', [])
        if a.get('actionType') == 0 and 'position' in a
    ]
    if passos:
        fluidez = round(len(set(passos)) / len(passos) * 100, 1)
    else:
        fluidez = 0.0

    return jsonify({
        "id_log": id_log,
        "metricas": {
            "precisao":  precisao,   # 0–100 — baseada em colisões vs ações
            "objetivos": objetivos,  # 0–100 — metas alcançadas / total
            "fluidez":   fluidez,    # 0–100 — posições únicas / passos totais
        },
        "atividade_finalizada": cleared,
        "nome_mapa": sessao.id_mapa,
    }), 200


# ==========================================
# ROTA 4: MÉTRICAS AGREGADAS DE TODAS AS SESSÕES DE UM ALUNO
# Ex: GET /api/analises/aluno/3/metricas
# Retorna média de Precisão, Objetivos e Fluidez de todas as sessões.
# ==========================================
def _calcular_metricas_sessao(dados):
    """Calcula as 3 métricas a partir do dados_log JSONB de uma sessão."""
    objectives = dados.get('objectives', [])
    results    = dados.get('results', {})
    cleared    = results.get('clearedMap', False)

    total_acoes    = sum(len(o.get('actions', []))    for o in objectives)
    total_colisoes = sum(len(o.get('collisions', [])) for o in objectives)
    total_eventos  = total_acoes + total_colisoes
    precisao = 100 * (1 - total_colisoes / total_eventos) if total_eventos > 0 else 100.0

    if cleared:
        objetivos = 100.0
    elif objectives:
        concluidos = sum(1 for o in objectives if (o.get('endTime') or 0) > 0)
        objetivos  = round(concluidos / len(objectives) * 100, 1)
    else:
        objetivos = 0.0

    passos = [
        (a['position']['x'], a['position']['z'])
        for o in objectives
        for a in o.get('actions', [])
        if a.get('actionType') == 0 and 'position' in a
    ]
    fluidez = round(len(set(passos)) / len(passos) * 100, 1) if passos else 0.0

    return {"precisao": precisao, "objetivos": objetivos, "fluidez": fluidez, "cleared": cleared}


@analises_bp.route('/aluno/<int:id_aluno>/metricas', methods=['GET'])
@jwt_required()
def metricas_aluno(id_aluno):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    aluno = Aluno.query.filter_by(id_aluno=id_aluno, id_professor_responsavel=professor.id_professor).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado ou sem permissão."}), 404

    sessoes = LogSessao.query.filter_by(id_aluno=id_aluno).all()
    validas = [s for s in sessoes if s.dados_log]

    if not validas:
        return jsonify({"erro": "Nenhuma sessão com dados disponível."}), 404

    resultados = [_calcular_metricas_sessao(s.dados_log) for s in validas]

    return jsonify({
        "id_aluno":      id_aluno,
        "total_sessoes": len(validas),
        "metricas": {
            "precisao":  round(sum(r["precisao"]  for r in resultados) / len(resultados), 1),
            "objetivos": round(sum(r["objetivos"] for r in resultados) / len(resultados), 1),
            "fluidez":   round(sum(r["fluidez"]   for r in resultados) / len(resultados), 1),
        },
        "atividade_finalizada": any(r["cleared"] for r in resultados),
    }), 200