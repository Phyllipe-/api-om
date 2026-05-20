import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime

from app import db, limiter
from app.models import Usuario, Professor, TipoPessoa

log = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

# Registro público habilitado via variável de ambiente (padrão: desabilitado)
_REGISTRO_PUBLICO = os.environ.get('REGISTRO_PUBLICO', 'false').lower() == 'true'


def _campos_professor(dados, prof):
    for campo in ('formacao_academica', 'telefone', 'tipo_endereco',
                  'nome_instituicao', 'cep', 'logradouro', 'registro_profissional'):
        if campo in dados:
            setattr(prof, campo, dados[campo])
    return prof


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute; 30 per hour")
def login():
    dados = request.get_json(silent=True) or request.form
    if not dados or 'email' not in dados or 'senha' not in dados:
        return jsonify({"erro": "Email e senha são obrigatórios."}), 400

    usuario = Usuario.query.filter_by(email=dados['email']).first()

    # Verificação em tempo constante para não vazar existência do e-mail
    senha_ok = check_password_hash(usuario.senha_hash, dados['senha']) if usuario else False

    if not usuario or not senha_ok:
        log.warning("Login falhou | email=%s | ip=%s", dados.get('email'), request.remote_addr)
        return jsonify({"erro": "Email ou senha incorretos."}), 401

    if not usuario.ativo:
        return jsonify({"erro": "Esta conta está desativada."}), 403

    log.info("Login OK | id=%s | ip=%s", usuario.id_usuario, request.remote_addr)
    token = create_access_token(
        identity=str(usuario.id_usuario),
        additional_claims={"id_tipo": usuario.id_tipo, "nome": usuario.nome_completo}
    )
    return jsonify({
        "mensagem": "Login realizado com sucesso!",
        "token": token,
        "usuario": {
            "id_usuario": usuario.id_usuario,
            "id_tipo":    usuario.id_tipo,
            "nome":       usuario.nome_completo,
        }
    }), 200


# ── CADASTRO PELO ADMINISTRADOR ───────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register_professor():
    if int(get_jwt_identity()) != 1:
        return jsonify({"erro": "Apenas o administrador pode cadastrar novos professores."}), 403

    dados = request.get_json()
    for campo in ('nome_completo', 'data_nascimento', 'email', 'senha'):
        if not dados.get(campo):
            return jsonify({"erro": f"O campo '{campo}' é obrigatório."}), 400

    if len(dados.get('senha', '')) < 8:
        return jsonify({"erro": "A senha deve ter pelo menos 8 caracteres."}), 400

    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({"erro": "Este e-mail já está cadastrado."}), 409

    try:
        tipo_prof  = TipoPessoa.query.filter_by(descricao="Professor").first()
        data_nasc  = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        novo_usuario = Usuario(
            id_tipo         = tipo_prof.id_tipo,
            nome_completo   = dados['nome_completo'],
            data_nascimento = data_nasc,
            email           = dados['email'],
            senha_hash      = generate_password_hash(dados['senha']),
        )
        db.session.add(novo_usuario)
        db.session.flush()
        novo_prof = Professor(id_usuario=novo_usuario.id_usuario)
        _campos_professor(dados, novo_prof)
        db.session.add(novo_prof)
        db.session.commit()
        log.info("Professor criado | id=%s | por admin", novo_usuario.id_usuario)
        return jsonify({"mensagem": "Professor cadastrado com sucesso!"}), 201
    except Exception:
        db.session.rollback()
        log.exception("Erro ao criar professor")
        return jsonify({"erro": "Falha ao criar conta. Tente novamente."}), 500


# ── AUTO-CADASTRO PÚBLICO ─────────────────────────────────────────────────────
@auth_bp.route('/register-public', methods=['POST'])
@limiter.limit("5 per hour")
def register_professor_publico():
    if not _REGISTRO_PUBLICO:
        return jsonify({"erro": "Registro público desabilitado."}), 403

    dados = request.get_json()
    for campo in ('nome_completo', 'data_nascimento', 'email', 'senha'):
        if not dados.get(campo):
            return jsonify({"erro": f"O campo '{campo}' é obrigatório."}), 400

    if len(dados.get('senha', '')) < 8:
        return jsonify({"erro": "A senha deve ter pelo menos 8 caracteres."}), 400

    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({"erro": "Este e-mail já está cadastrado."}), 409

    try:
        tipo_prof = TipoPessoa.query.filter_by(descricao="Professor").first()
        data_nasc = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        novo_usuario = Usuario(
            id_tipo         = tipo_prof.id_tipo,
            nome_completo   = dados['nome_completo'],
            data_nascimento = data_nasc,
            email           = dados['email'],
            senha_hash      = generate_password_hash(dados['senha']),
        )
        db.session.add(novo_usuario)
        db.session.flush()
        novo_prof = Professor(id_usuario=novo_usuario.id_usuario)
        _campos_professor(dados, novo_prof)
        db.session.add(novo_prof)
        db.session.commit()
        log.info("Auto-cadastro | id=%s | ip=%s", novo_usuario.id_usuario, request.remote_addr)
        return jsonify({"mensagem": "Conta criada com sucesso!"}), 201
    except Exception:
        db.session.rollback()
        log.exception("Erro no auto-cadastro")
        return jsonify({"erro": "Falha ao criar conta. Tente novamente."}), 500


# ── CHECK EMAIL (pública, rate-limited) ──────────────────────────────────────
@auth_bp.route('/check-email', methods=['GET'])
@limiter.limit("20 per minute")
def check_email():
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({"erro": "Parâmetro 'email' é obrigatório."}), 400
    existe = Usuario.query.filter_by(email=email).first() is not None
    return jsonify({"disponivel": not existe}), 200
