from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import Professor, TipoPessoa, LogSessao, Lateralidade, SimulacaoTrajetoria, Trafego, Giros, Comparacao

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