from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from app import db
from app.models import Usuario, Professor, Aluno, Mapa, LogSessao, Atividade

professores_bp = Blueprint('professores', __name__)


def _prof_dict(prof, usr):
    return {
        "id_professor": prof.id_professor,
        "id_usuario": usr.id_usuario,
        "nome_completo": usr.nome_completo,
        "email": usr.email,
        "data_nascimento": usr.data_nascimento.isoformat() if usr.data_nascimento else None,
        "registro_profissional": prof.registro_profissional,
        "ativo": usr.ativo
    }


def _require_admin():
    """Retorna (id_usuario, None) se admin, ou (None, response) se não."""
    try:
        uid = int(get_jwt_identity())
    except Exception:
        return None, (jsonify({"erro": "Não autorizado."}), 401)
    if uid != 1:
        return None, (jsonify({"erro": "Acesso restrito ao administrador."}), 403)
    return uid, None


# ==========================================
# ROTA 1: LISTAR TODOS OS PROFESSORES
# ==========================================
@professores_bp.route('/', methods=['GET'])
@jwt_required()
def listar_professores():
    _, err = _require_admin()
    if err:
        return err

    profs = Professor.query.all()
    lista = [_prof_dict(p, Usuario.query.get(p.id_usuario)) for p in profs]
    return jsonify({"total": len(lista), "professores": lista}), 200


# ==========================================
# ROTA 2: DETALHE DE UM PROFESSOR
# ==========================================
@professores_bp.route('/<int:id_professor>', methods=['GET'])
@jwt_required()
def detalhar_professor(id_professor):
    _, err = _require_admin()
    if err:
        return err

    prof = Professor.query.get(id_professor)
    if not prof:
        return jsonify({"erro": "Professor não encontrado."}), 404

    usr = Usuario.query.get(prof.id_usuario)
    return jsonify(_prof_dict(prof, usr)), 200


# ==========================================
# ROTA 3: EDITAR PROFESSOR
# ==========================================
@professores_bp.route('/<int:id_professor>', methods=['PATCH'])
@jwt_required()
def editar_professor(id_professor):
    _, err = _require_admin()
    if err:
        return err

    prof = Professor.query.get(id_professor)
    if not prof:
        return jsonify({"erro": "Professor não encontrado."}), 404

    usr = Usuario.query.get(prof.id_usuario)
    dados = request.get_json()

    if 'nome_completo' in dados and dados['nome_completo'].strip():
        usr.nome_completo = dados['nome_completo'].strip()

    if 'email' in dados and dados['email'].strip():
        novo_email = dados['email'].strip()
        if novo_email != usr.email and Usuario.query.filter_by(email=novo_email).first():
            return jsonify({"erro": "Este email já está em uso."}), 409
        usr.email = novo_email

    if 'data_nascimento' in dados and dados['data_nascimento']:
        try:
            usr.data_nascimento = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD."}), 400

    if 'registro_profissional' in dados:
        prof.registro_profissional = dados['registro_profissional']

    if 'nova_senha' in dados and dados['nova_senha']:
        usr.senha_hash = generate_password_hash(dados['nova_senha'])

    if 'ativo' in dados:
        # Impede desativar o próprio admin
        if usr.id_usuario == 1 and not dados['ativo']:
            return jsonify({"erro": "Não é possível desativar o administrador."}), 400
        usr.ativo = bool(dados['ativo'])

    db.session.commit()
    return jsonify(_prof_dict(prof, usr)), 200


# ==========================================
# ROTA 4: ATIVAR / DESATIVAR PROFESSOR
# ==========================================
@professores_bp.route('/<int:id_professor>/ativo', methods=['PATCH'])
@jwt_required()
def toggle_ativo_professor(id_professor):
    _, err = _require_admin()
    if err:
        return err

    prof = Professor.query.get(id_professor)
    if not prof:
        return jsonify({"erro": "Professor não encontrado."}), 404

    usr = Usuario.query.get(prof.id_usuario)
    if usr.id_usuario == 1:
        return jsonify({"erro": "Não é possível desativar o administrador."}), 400

    usr.ativo = not usr.ativo
    db.session.commit()
    return jsonify({"id_professor": id_professor, "ativo": usr.ativo}), 200


# ==========================================
# ROTA 5: REMOVER PROFESSOR
# ==========================================
@professores_bp.route('/<int:id_professor>', methods=['DELETE'])
@jwt_required()
def remover_professor(id_professor):
    _, err = _require_admin()
    if err:
        return err

    prof = Professor.query.get(id_professor)
    if not prof:
        return jsonify({"erro": "Professor não encontrado."}), 404

    usr = Usuario.query.get(prof.id_usuario)
    if usr.id_usuario == 1:
        return jsonify({"erro": "Não é possível remover o administrador."}), 400

    # Bloqueia se existirem dependências
    tem_alunos    = Aluno.query.filter_by(id_professor_responsavel=prof.id_professor).first()
    tem_mapas     = Mapa.query.filter_by(id_criador=prof.id_professor).first()
    tem_atividades = Atividade.query.filter_by(id_professor=prof.id_professor).first()
    tem_sessoes   = LogSessao.query.filter_by(id_criador=prof.id_professor).first()

    pendencias = []
    if tem_alunos:     pendencias.append("alunos vinculados")
    if tem_mapas:      pendencias.append("mapas criados")
    if tem_atividades: pendencias.append("atividades criadas")
    if tem_sessoes:    pendencias.append("sessões registradas")

    if pendencias:
        return jsonify({
            "erro": f"Não é possível remover este professor pois ele possui {', '.join(pendencias)}."
        }), 409

    try:
        db.session.delete(prof)
        db.session.delete(usr)
        db.session.commit()
        return jsonify({"mensagem": "Professor removido com sucesso."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Falha ao remover: {str(e)}"}), 500
