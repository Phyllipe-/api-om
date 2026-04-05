from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

from app import db
from app.models import Professor, Aluno, Mapa, Atividade, AtividadeMapa, AtividadeAluno, Usuario, TipoPessoa

atividades_bp = Blueprint('atividades', __name__)


def _professor_from_request():
    """Retorna o Professor do usuário logado ou None."""
    id_usuario = get_jwt_identity()
    return Professor.query.filter_by(id_usuario=id_usuario).first()


def _serializar_atividade(at, incluir_detalhes=False):
    prof = Professor.query.get(at.id_professor)
    usr  = Usuario.query.get(prof.id_usuario) if prof else None
    dados = {
        "id_atividade": at.id_atividade,
        "nome":         at.nome,
        "descricao":    at.descricao,
        "ativo":        at.ativo,
        "data_criacao": at.data_criacao.strftime("%Y-%m-%d %H:%M"),
        "nome_professor": usr.nome_completo if usr else "—",
        "total_mapas":  AtividadeMapa.query.filter_by(id_atividade=at.id_atividade).count(),
        "total_alunos": AtividadeAluno.query.filter_by(id_atividade=at.id_atividade).count(),
    }
    if incluir_detalhes:
        mapas = (
            AtividadeMapa.query
            .filter_by(id_atividade=at.id_atividade)
            .order_by(AtividadeMapa.ordem)
            .all()
        )
        dados["mapas"] = [
            {"id_mapa": am.id_mapa, "ordem": am.ordem,
             "nome_mapa": Mapa.query.get(am.id_mapa).nome_mapa if Mapa.query.get(am.id_mapa) else "—"}
            for am in mapas
        ]
        alunos = AtividadeAluno.query.filter_by(id_atividade=at.id_atividade).all()
        dados["alunos"] = [
            {"id_aluno": aa.id_aluno,
             "nome_completo": (lambda a: Usuario.query.get(a.id_usuario).nome_completo if a else "—")(Aluno.query.get(aa.id_aluno))}
            for aa in alunos
        ]
    return dados


# ==========================================
# ROTA 1: CRIAR ATIVIDADE
# ==========================================
@atividades_bp.route('/', methods=['POST'])
@jwt_required()
def criar_atividade():
    claims = get_jwt()
    tipo_prof = TipoPessoa.query.filter_by(descricao="Professor").first()
    if claims.get('id_tipo') != tipo_prof.id_tipo:
        return jsonify({"erro": "Apenas professores podem criar atividades."}), 403

    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    dados = request.get_json()
    if not dados or not dados.get('nome'):
        return jsonify({"erro": "O campo 'nome' é obrigatório."}), 400

    mapas_payload = dados.get('mapas', [])   # [{"id_mapa": int, "ordem": int}]
    alunos_ids    = dados.get('alunos', [])  # [int]

    if not mapas_payload:
        return jsonify({"erro": "A atividade deve ter ao menos um mapa."}), 400

    try:
        nova = Atividade(
            nome=dados['nome'],
            descricao=dados.get('descricao', ''),
            id_professor=professor.id_professor
        )
        db.session.add(nova)
        db.session.flush()

        for item in mapas_payload:
            db.session.add(AtividadeMapa(
                id_atividade=nova.id_atividade,
                id_mapa=item['id_mapa'],
                ordem=item['ordem']
            ))

        for id_aluno in alunos_ids:
            aluno = Aluno.query.filter_by(
                id_aluno=id_aluno,
                id_professor_responsavel=professor.id_professor
            ).first()
            if aluno:
                db.session.add(AtividadeAluno(
                    id_atividade=nova.id_atividade,
                    id_aluno=id_aluno
                ))

        db.session.commit()
        return jsonify({"mensagem": "Atividade criada com sucesso!", "id_atividade": nova.id_atividade}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao criar atividade: {str(e)}"}), 500


# ==========================================
# ROTA 2: LISTAR ATIVIDADES DO PROFESSOR
# ==========================================
@atividades_bp.route('/', methods=['GET'])
@jwt_required()
def listar_atividades():
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    atividades = (
        Atividade.query
        .filter_by(id_professor=professor.id_professor)
        .order_by(Atividade.data_criacao.desc())
        .all()
    )
    return jsonify({
        "total": len(atividades),
        "atividades": [_serializar_atividade(a) for a in atividades]
    }), 200


# ==========================================
# ROTA 3: DETALHE DE UMA ATIVIDADE
# ==========================================
@atividades_bp.route('/<int:id_atividade>', methods=['GET'])
@jwt_required()
def detalhar_atividade(id_atividade):
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    at = Atividade.query.filter_by(
        id_atividade=id_atividade,
        id_professor=professor.id_professor
    ).first()
    if not at:
        return jsonify({"erro": "Atividade não encontrada."}), 404

    return jsonify(_serializar_atividade(at, incluir_detalhes=True)), 200


# ==========================================
# ROTA 4: ATIVAR / DESATIVAR ATIVIDADE
# ==========================================
@atividades_bp.route('/<int:id_atividade>/ativo', methods=['PATCH'])
@jwt_required()
def toggle_ativo(id_atividade):
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    at = Atividade.query.filter_by(
        id_atividade=id_atividade,
        id_professor=professor.id_professor
    ).first()
    if not at:
        return jsonify({"erro": "Atividade não encontrada."}), 404

    at.ativo = not at.ativo
    db.session.commit()
    return jsonify({"id_atividade": id_atividade, "ativo": at.ativo}), 200


# ==========================================
# ROTA 5: ATIVIDADE ATIVA DE UM ALUNO
# ==========================================
@atividades_bp.route('/para-aluno/<int:id_aluno>', methods=['GET'])
@jwt_required()
def atividade_para_aluno(id_aluno):
    """
    Retorna a atividade ativa mais recente atribuída ao aluno pelo professor logado,
    com os mapas ordenados e seus caminhos de arquivo.
    """
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    # Verifica que o aluno pertence a este professor
    aluno = Aluno.query.filter_by(
        id_aluno=id_aluno,
        id_professor_responsavel=professor.id_professor
    ).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado ou sem permissão."}), 404

    # Busca a atividade ativa mais recente que contém este aluno
    atividade = (
        Atividade.query
        .join(AtividadeAluno, AtividadeAluno.id_atividade == Atividade.id_atividade)
        .filter(
            Atividade.id_professor == professor.id_professor,
            Atividade.ativo == True,
            AtividadeAluno.id_aluno == id_aluno
        )
        .order_by(Atividade.data_criacao.desc())
        .first()
    )
    if not atividade:
        return jsonify({"erro": "Nenhuma atividade ativa encontrada para este aluno."}), 404

    mapas = (
        AtividadeMapa.query
        .filter_by(id_atividade=atividade.id_atividade)
        .order_by(AtividadeMapa.ordem)
        .all()
    )

    mapas_payload = []
    for am in mapas:
        mapa = Mapa.query.get(am.id_mapa)
        if mapa:
            mapas_payload.append({
                "id_mapa": mapa.id_mapa,
                "ordem": am.ordem,
                "nome_mapa": mapa.nome_mapa,
                "caminho_arquivo_xml": mapa.caminho_arquivo_xml,
                "caminho_preview": mapa.caminho_preview,
            })

    return jsonify({
        "id_atividade": atividade.id_atividade,
        "nome": atividade.nome,
        "descricao": atividade.descricao,
        "mapas": mapas_payload
    }), 200
