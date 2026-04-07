from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, decode_token
from datetime import datetime
import os, json

from app import db
from app.models import Professor, Aluno, Mapa, LogSessao, TipoPessoa, Usuario
from app.utils import arquivo_permitido, salvar_arquivo_seguro, EXTENSOES_MAPA

EXTENSOES_PREVIEW = {'png', 'jpg', 'jpeg', 'webp'}

treinos_bp = Blueprint('treinos', __name__)

# ==========================================
# ROTA 1: FAZER UPLOAD E REGISTAR NOVO MAPA
# ==========================================
@treinos_bp.route('/mapas', methods=['POST'])
@jwt_required()
def registar_mapa():
    id_usuario_logado = get_jwt_identity()
    claims = get_jwt()
    
    if claims.get('id_tipo') != 1: 
        return jsonify({"erro": "Apenas professores podem registar mapas."}), 403

    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()

    if 'arquivo_mapa' not in request.files:
        return jsonify({"erro": "Nenhum ficheiro de mapa foi enviado."}), 400
    
    arquivo = request.files['arquivo_mapa']
    nome_mapa = request.form.get('nome_mapa') 

    if not nome_mapa or arquivo.filename == '':
        return jsonify({"erro": "Nome do mapa e o ficheiro são obrigatórios."}), 400

    if not arquivo_permitido(arquivo.filename, EXTENSOES_MAPA):
        return jsonify({"erro": "Tipo de ficheiro inválido. Apenas .xml ou .json são permitidos."}), 400

    try:
        # Garante que a pasta de previews existe
        pasta_previews = os.path.join(current_app.config['UPLOAD_FOLDER'], 'previews')
        os.makedirs(pasta_previews, exist_ok=True)

        caminho_relativo = salvar_arquivo_seguro(arquivo, 'mapas', current_app.config['UPLOAD_FOLDER'])

        # Preview opcional
        caminho_preview = None
        arquivo_preview = request.files.get('arquivo_preview')
        if arquivo_preview and arquivo_preview.filename:
            if arquivo_permitido(arquivo_preview.filename, EXTENSOES_PREVIEW):
                caminho_preview = salvar_arquivo_seguro(arquivo_preview, 'previews', current_app.config['UPLOAD_FOLDER'])

        novo_mapa = Mapa(
            nome_mapa=nome_mapa,
            id_criador=professor.id_professor,
            caminho_arquivo_xml=caminho_relativo,
            caminho_preview=caminho_preview
        )
        db.session.add(novo_mapa)
        db.session.commit()

        return jsonify({
            "mensagem": "Upload do mapa realizado com sucesso!",
            "id_mapa": novo_mapa.id_mapa,
            "caminho": caminho_relativo,
            "caminho_preview": caminho_preview
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao processar o arquivo: {str(e)}"}), 500


# ==========================================
# ROTA 2: LISTAR TODOS OS MAPAS
# ==========================================
@treinos_bp.route('/mapas', methods=['GET'])
@jwt_required()
def listar_mapas():
    mapas = Mapa.query.order_by(Mapa.data_criacao.desc()).all()
    lista_mapas = []

    for mapa in mapas:
        prof = Professor.query.get(mapa.id_criador)
        usr = Usuario.query.get(prof.id_usuario) if prof else None
        lista_mapas.append({
            "id_mapa": mapa.id_mapa,
            "nome_mapa": mapa.nome_mapa,
            "caminho_arquivo_xml": mapa.caminho_arquivo_xml,
            "caminho_preview": mapa.caminho_preview,
            "data_criacao": mapa.data_criacao.strftime("%Y-%m-%d %H:%M"),
            "ativo": mapa.ativo,
            "id_criador": mapa.id_criador,
            "nome_professor": usr.nome_completo if usr else "—"
        })

    return jsonify({"total": len(lista_mapas), "mapas": lista_mapas}), 200


# ==========================================
# ROTA 2B: LISTAR APENAS MAPAS DO PROFESSOR LOGADO
# ==========================================
@treinos_bp.route('/mapas/meus', methods=['GET'])
@jwt_required()
def listar_meus_mapas():
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    mapas = Mapa.query.filter_by(id_criador=professor.id_professor).order_by(Mapa.data_criacao.desc()).all()
    lista_mapas = []

    for mapa in mapas:
        lista_mapas.append({
            "id_mapa": mapa.id_mapa,
            "nome_mapa": mapa.nome_mapa,
            "caminho_arquivo_xml": mapa.caminho_arquivo_xml,
            "caminho_preview": mapa.caminho_preview,
            "data_criacao": mapa.data_criacao.strftime("%Y-%m-%d %H:%M"),
            "ativo": mapa.ativo
        })

    return jsonify({"total": len(lista_mapas), "mapas": lista_mapas}), 200


# ==========================================
# ROTA 2C: ATIVAR / DESATIVAR MAPA (SOMENTE DO PROFESSOR LOGADO)
# ==========================================
@treinos_bp.route('/mapas/<int:id_mapa>/ativo', methods=['PATCH'])
@jwt_required()
def toggle_mapa_ativo(id_mapa):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    mapa = Mapa.query.filter_by(id_mapa=id_mapa, id_criador=professor.id_professor).first()
    if not mapa:
        return jsonify({"erro": "Mapa não encontrado ou sem permissão."}), 404

    mapa.ativo = not mapa.ativo
    db.session.commit()

    return jsonify({"id_mapa": id_mapa, "ativo": mapa.ativo}), 200


# ==========================================
# ROTA 2D: LISTAR SESSÕES DE UM ALUNO
# ==========================================
@treinos_bp.route('/sessoes', methods=['GET'])
@jwt_required()
def listar_sessoes():
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    id_aluno = request.args.get('id_aluno', type=int)
    if not id_aluno:
        return jsonify({"erro": "Parâmetro 'id_aluno' é obrigatório."}), 400

    aluno = Aluno.query.filter_by(
        id_aluno=id_aluno,
        id_professor_responsavel=professor.id_professor
    ).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado ou sem permissão."}), 404

    sessoes = (
        LogSessao.query
        .filter_by(id_aluno=id_aluno)
        .order_by(LogSessao.data_criacao_arquivo_log.desc())
        .all()
    )

    lista = []
    for s in sessoes:
        mapa = Mapa.query.get(s.id_mapa)
        dados = s.dados_log or {}
        results = dados.get('results', {})
        lista.append({
            "id_log":        s.id_log,
            "id_mapa":       s.id_mapa,
            "nome_mapa":     mapa.nome_mapa if mapa else "—",
            "data":          s.data_criacao_arquivo_log.strftime("%Y-%m-%d %H:%M"),
            "cleared_map":   results.get('clearedMap', False),
            "tempo_sessao":  results.get('totalSessionTime'),
            "tem_minimap":   bool(s.caminho_minimap),
        })

    return jsonify({"total": len(lista), "sessoes": lista}), 200


# ==========================================
# ROTA 2E: DETALHE DE UMA SESSÃO
# ==========================================
@treinos_bp.route('/sessoes/<int:id_log>', methods=['GET'])
@jwt_required()
def detalhe_sessao(id_log):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    s = LogSessao.query.filter_by(id_log=id_log, id_criador=professor.id_professor).first()
    if not s:
        return jsonify({"erro": "Sessão não encontrada ou sem permissão."}), 404

    mapa   = Mapa.query.get(s.id_mapa)
    dados  = s.dados_log or {}
    results = dados.get('results', {})

    objectives = dados.get('objectives', [])
    total_acoes    = sum(len(o.get('actions', []))    for o in objectives)
    total_colisoes = sum(len(o.get('collisions', [])) for o in objectives)

    return jsonify({
        "id_log":          s.id_log,
        "id_mapa":         s.id_mapa,
        "nome_mapa":       mapa.nome_mapa if mapa else "—",
        "data":            s.data_criacao_arquivo_log.strftime("%Y-%m-%d %H:%M"),
        "cleared_map":     results.get('clearedMap', False),
        "tempo_sessao":    results.get('totalSessionTime'),
        "total_acoes":     total_acoes,
        "total_colisoes":  total_colisoes,
        "total_objetivos": len(objectives),
        "objetivos_concluidos": sum(1 for o in objectives if (o.get('endTime') or 0) > 0),
        "caminho_minimap": s.caminho_minimap,
        "tem_minimap":     bool(s.caminho_minimap),
        "render_3d":       mapa.caminho_render_3d if mapa else None,
    }), 200


# ==========================================
# ROTA 3: REGISTAR SESSÃO DE TREINO (LOG)
# ==========================================
@treinos_bp.route('/sessoes', methods=['POST'])
@jwt_required()
def registar_sessao():
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    
    if not professor:
        return jsonify({"erro": "Apenas professores podem registar sessões de treino."}), 403

    # Validação dos dados do formulário e do arquivo
    if 'arquivo_log' not in request.files:
        return jsonify({"erro": "Nenhum arquivo de log foi enviado."}), 400

    arquivo = request.files['arquivo_log']
    id_aluno = request.form.get('id_aluno', type=int)
    id_mapa = request.form.get('id_mapa', type=int)

    if not id_aluno or not id_mapa or arquivo.filename == '':
        return jsonify({"erro": "Os campos 'id_aluno', 'id_mapa' e o 'arquivo_log' são obrigatórios."}), 400

    # Verifica se o aluno existe e pertence a este professor
    aluno = Aluno.query.filter_by(id_aluno=id_aluno).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado."}), 404
    
    if aluno.id_professor_responsavel != professor.id_professor:
        return jsonify({"erro": "Este aluno não está sob a sua responsabilidade."}), 403

    # Verifica se o mapa existe
    mapa = Mapa.query.filter_by(id_mapa=id_mapa).first()
    if not mapa:
        return jsonify({"erro": "Mapa não encontrado."}), 404

    id_atividade = request.form.get('id_atividade', type=int)

    try:
        # Salva arquivo .json bruto
        pasta_sessoes = os.path.join(current_app.config['UPLOAD_FOLDER'], 'sessoes')
        os.makedirs(pasta_sessoes, exist_ok=True)
        caminho_relativo = salvar_arquivo_seguro(arquivo, 'sessoes', current_app.config['UPLOAD_FOLDER'])

        # Parseia conteúdo do log para JSONB
        arquivo.stream.seek(0)
        try:
            dados_log = json.load(arquivo.stream)
        except Exception:
            dados_log = None

        # Minimap (opcional)
        caminho_minimap = None
        arquivo_minimap = request.files.get('minimap')
        if arquivo_minimap and arquivo_minimap.filename:
            pasta_minimaps = os.path.join(current_app.config['UPLOAD_FOLDER'], 'minimaps')
            os.makedirs(pasta_minimaps, exist_ok=True)
            caminho_minimap = salvar_arquivo_seguro(arquivo_minimap, 'minimaps', current_app.config['UPLOAD_FOLDER'])

        nova_sessao = LogSessao(
            id_aluno=aluno.id_aluno,
            id_criador=professor.id_professor,
            id_mapa=mapa.id_mapa,
            id_atividade=id_atividade,
            caminho_arquivo_log=caminho_relativo,
            dados_log=dados_log,
            caminho_minimap=caminho_minimap
        )
        db.session.add(nova_sessao)
        db.session.commit()

        return jsonify({"mensagem": "Sessão de treino registada com sucesso!", "id_log": nova_sessao.id_log}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao registar sessão: {str(e)}"}), 500
    
    
# ==========================================
# ROTA 4: SERVIR ARQUIVOS PARA O FRONTEND
# Aceita JWT via header Authorization OU query param ?token=
# Ex: GET /api/treinos/arquivos/minimaps/aluno_14_...png?token=<jwt>
# ==========================================
@treinos_bp.route('/arquivos/<pasta>/<nome_arquivo>', methods=['GET'])
def baixar_arquivo(pasta, nome_arquivo):
    # Autenticação: header Bearer ou query param token
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request()
    except Exception:
        token_param = request.args.get('token')
        if not token_param:
            return jsonify({"erro": "Token não fornecido."}), 401
        try:
            decode_token(token_param)
        except Exception:
            return jsonify({"erro": "Token inválido."}), 401

    if pasta not in ['mapas', 'sessoes', 'analises', 'minimaps', 'renders3d']:
        return jsonify({"erro": "Acesso negado à pasta solicitada."}), 403

    pasta_alvo = os.path.join(current_app.config['UPLOAD_FOLDER'], pasta)
    return send_from_directory(pasta_alvo, nome_arquivo)


# ==========================================
# ROTA 5: APROPRIAR MAPA DE OUTRO PROFESSOR
# Cria uma cópia do registro apontando para os mesmos arquivos
# ==========================================
@treinos_bp.route('/mapas/<int:id_mapa>/apropriar', methods=['POST'])
@jwt_required()
def apropriar_mapa(id_mapa):
    id_usuario_logado = get_jwt_identity()
    claims = get_jwt()

    tipo_prof = TipoPessoa.query.filter_by(descricao="Professor").first()
    if claims.get('id_tipo') != tipo_prof.id_tipo:
        return jsonify({"erro": "Apenas professores podem apropriar mapas."}), 403

    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    original = Mapa.query.get(id_mapa)
    if not original:
        return jsonify({"erro": "Mapa não encontrado."}), 404

    if original.id_criador == professor.id_professor:
        return jsonify({"erro": "Este mapa já é seu."}), 409

    # Impede duplicata: mesmo arquivo já apropriado antes
    existente = Mapa.query.filter_by(
        id_criador=professor.id_professor,
        caminho_arquivo_xml=original.caminho_arquivo_xml
    ).first()
    if existente:
        return jsonify({"erro": "Você já possui este mapa.", "id_mapa": existente.id_mapa}), 409

    try:
        copia = Mapa(
            nome_mapa=f"Cópia de {original.nome_mapa}",
            id_criador=professor.id_professor,
            caminho_arquivo_xml=original.caminho_arquivo_xml,
            caminho_preview=original.caminho_preview
        )
        db.session.add(copia)
        db.session.commit()
        return jsonify({
            "mensagem": "Mapa apropriado com sucesso!",
            "id_mapa": copia.id_mapa,
            "nome_mapa": copia.nome_mapa
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao apropriar mapa: {str(e)}"}), 500


# ==========================================
# ROTA 6: ATUALIZAR PREVIEW DE MAPA (screenshot 3D capturado pelo ENA)
# Ex: PATCH /api/treinos/mapas/<id>/preview
# ==========================================
@treinos_bp.route('/mapas/<int:id_mapa>/preview', methods=['PATCH'])
@jwt_required()
def atualizar_preview(id_mapa):
    id_usuario_logado = get_jwt_identity()
    claims = get_jwt()

    if claims.get('id_tipo') != 1:
        return jsonify({"erro": "Apenas professores podem atualizar previews."}), 403

    mapa = Mapa.query.get(id_mapa)
    if not mapa:
        return jsonify({"erro": "Mapa não encontrado."}), 404

    arquivo_preview = request.files.get('arquivo_preview')
    if not arquivo_preview or not arquivo_preview.filename:
        return jsonify({"erro": "Nenhum arquivo de preview enviado."}), 400

    if not arquivo_permitido(arquivo_preview.filename, EXTENSOES_PREVIEW):
        return jsonify({"erro": "Formato inválido. Use PNG, JPG ou WEBP."}), 400

    try:
        pasta_previews = os.path.join(current_app.config['UPLOAD_FOLDER'], 'previews')
        os.makedirs(pasta_previews, exist_ok=True)

        # Remove preview anterior se existir
        if mapa.caminho_preview:
            caminho_antigo = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                          mapa.caminho_preview.lstrip('/'))
            if os.path.exists(caminho_antigo):
                os.remove(caminho_antigo)

        novo_caminho = salvar_arquivo_seguro(arquivo_preview, 'previews',
                                             current_app.config['UPLOAD_FOLDER'])
        mapa.caminho_preview = novo_caminho
        db.session.commit()

        return jsonify({"mensagem": "Preview atualizado com sucesso.", "caminho_preview": novo_caminho}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar preview: {str(e)}"}), 500


# ==========================================
# ROTA 7: SERVIR PREVIEW DE MAPA (sem autenticação — imagens públicas)
# Ex: GET /api/treinos/mapas/<id>/preview
# ==========================================
@treinos_bp.route('/mapas/<int:id_mapa>/preview', methods=['GET'])
def servir_preview(id_mapa):
    mapa = Mapa.query.get(id_mapa)
    if not mapa or not mapa.caminho_preview:
        return jsonify({"erro": "Preview não disponível."}), 404

    # caminho_preview é "/previews/nome.png"
    nome_arquivo = os.path.basename(mapa.caminho_preview)
    pasta_alvo = os.path.join(current_app.config['UPLOAD_FOLDER'], 'previews')
    return send_from_directory(pasta_alvo, nome_arquivo)


# ==========================================
# ROTA 8: RECEBER RENDER 3D DO ENA
# Ex: POST /api/treinos/mapas/<id>/render3d
# Chamado pelo ENA na primeira vez que o jogador entra no mapa.
# Salva em uploads/renders3d/ e registra em mapa.caminho_render_3d.
# ==========================================
@treinos_bp.route('/mapas/<int:id_mapa>/render3d', methods=['POST'])
@jwt_required()
def receber_render3d(id_mapa):
    mapa = Mapa.query.get(id_mapa)
    if not mapa:
        return jsonify({"erro": "Mapa não encontrado."}), 404

    arquivo = request.files.get('render3d')
    if not arquivo or not arquivo.filename:
        return jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'render3d'."}), 400

    if not arquivo_permitido(arquivo.filename, EXTENSOES_PREVIEW):
        return jsonify({"erro": "Formato inválido. Use PNG, JPG ou WEBP."}), 400

    try:
        pasta = os.path.join(current_app.config['UPLOAD_FOLDER'], 'renders3d')
        os.makedirs(pasta, exist_ok=True)

        caminho = salvar_arquivo_seguro(arquivo, 'renders3d', current_app.config['UPLOAD_FOLDER'])
        mapa.caminho_render_3d = caminho
        db.session.commit()

        return jsonify({
            "mensagem": "Render 3D recebido com sucesso.",
            "id_mapa": id_mapa,
            "caminho_render_3d": caminho
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar render: {str(e)}"}), 500


# ==========================================
# ROTA 9: SERVIR RENDER 3D
# Ex: GET /api/treinos/mapas/<id>/render3d
# ==========================================
@treinos_bp.route('/mapas/<int:id_mapa>/render3d', methods=['GET'])
def servir_render3d(id_mapa):
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request()
    except Exception:
        token_param = request.args.get('token')
        if not token_param:
            return jsonify({"erro": "Token não fornecido."}), 401
        try:
            decode_token(token_param)
        except Exception:
            return jsonify({"erro": "Token inválido."}), 401

    mapa = Mapa.query.get(id_mapa)
    if not mapa or not mapa.caminho_render_3d:
        return jsonify({"erro": "Render 3D não disponível."}), 404

    nome_arquivo = os.path.basename(mapa.caminho_render_3d)
    pasta_alvo = os.path.join(current_app.config['UPLOAD_FOLDER'], 'renders3d')
    return send_from_directory(pasta_alvo, nome_arquivo)