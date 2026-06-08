import os
import logging
import hashlib
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, decode_token
from datetime import datetime, timedelta

from app import db, limiter
from app.models import Usuario, Professor, TipoPessoa
from app.utils import enviar_email

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
            "senha_provisoria": bool(usuario.senha_provisoria),
        }
    }), 200


# ── CADASTRO PELO ADMINISTRADOR ───────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register_professor():
    if int(get_jwt_identity()) != 1:
        return jsonify({"erro": "Apenas o administrador pode cadastrar novos professores."}), 403

    dados = request.get_json()
    for campo in ('nome_completo', 'email', 'senha'):
        if not dados.get(campo):
            return jsonify({"erro": f"O campo '{campo}' é obrigatório."}), 400

    if len(dados.get('senha', '')) < 8:
        return jsonify({"erro": "A senha deve ter pelo menos 8 caracteres."}), 400

    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({"erro": "Este e-mail já está cadastrado."}), 409

    try:
        tipo_prof  = TipoPessoa.query.filter_by(descricao="Professor").first()
        data_nasc  = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date() if dados.get('data_nascimento') else None
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
    for campo in ('nome_completo', 'email', 'senha'):
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


# ── REDEFINIÇÃO DE SENHA (professores) ───────────────────────────────────────
# Token de reset é um JWT { tipo:"reset_senha", chk } com exp de 24h.
# 'chk' deriva do senha_hash atual → uso único: ao trocar a senha, o link morre.
_RESET_VALIDADE_HORAS = 24


def _chk_senha(senha_hash):
    return hashlib.sha256((senha_hash or "").encode()).hexdigest()[:16]


def _gerar_token_reset(usuario):
    return create_access_token(
        identity=str(usuario.id_usuario),
        additional_claims={"tipo": "reset_senha", "chk": _chk_senha(usuario.senha_hash)},
        expires_delta=timedelta(hours=_RESET_VALIDADE_HORAS),
    )


def _url_reset(token):
    base = os.environ.get('RESET_LINK_BASE', 'https://mova.omaproject.com.br/redefinir-senha')
    return f"{base}?t={token}"


def _email_reset_html(nome, url):
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:auto;color:#1e293b;">
      <h2 style="margin:0 0 .5rem;">Redefinição de senha — MOVA</h2>
      <p>Olá, {nome}. Recebemos um pedido para redefinir a sua senha.</p>
      <p style="margin:1.2rem 0;">
        <a href="{url}" style="background:#1e293b;color:#fff;padding:11px 20px;border-radius:6px;text-decoration:none;display:inline-block;">Redefinir senha</a>
      </p>
      <p style="font-size:.9em;color:#475569;">Ou copie e cole este link no navegador:<br>
        <a href="{url}" style="color:#2563eb;word-break:break-all;">{url}</a>
      </p>
      <p style="font-size:.85em;color:#94a3b8;">O link expira em {_RESET_VALIDADE_HORAS} horas. Se você não fez este pedido, ignore este e-mail.</p>
    </div>
    """


# Self-service: professor pede o link pelo e-mail.
@auth_bp.route('/esqueci-senha', methods=['POST'])
@limiter.limit("5 per 15 minutes; 20 per day")
def esqueci_senha():
    dados = request.get_json(silent=True) or {}
    email = (dados.get('email') or '').strip().lower()

    # Resposta sempre genérica (não revela se o e-mail existe).
    resposta = {"mensagem": "Se o e-mail estiver cadastrado, enviaremos um link de redefinição."}
    if not email:
        return jsonify(resposta), 200

    usuario = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()
    if usuario and usuario.ativo and Professor.query.filter_by(id_usuario=usuario.id_usuario).first():
        token = _gerar_token_reset(usuario)
        enviar_email(usuario.email, "Redefinição de senha - MOVA",
                     _email_reset_html(usuario.nome_completo, _url_reset(token)))
        log.info("Reset solicitado | id=%s | ip=%s", usuario.id_usuario, request.remote_addr)

    return jsonify(resposta), 200


# Redefine a senha a partir do token (link). Token vem no corpo.
@auth_bp.route('/redefinir-senha', methods=['POST'])
@limiter.limit("10 per 15 minutes")
def redefinir_senha():
    dados = request.get_json(silent=True) or {}
    token = (dados.get('token') or '').strip()
    nova  = dados.get('nova_senha') or ''

    if not token or not nova:
        return jsonify({"erro": "Token e nova senha são obrigatórios."}), 400
    if len(nova) < 8:
        return jsonify({"erro": "A senha deve ter pelo menos 8 caracteres."}), 400

    try:
        claims = decode_token(token)
    except Exception:
        return jsonify({"erro": "Link inválido ou expirado. Peça um novo."}), 400

    if claims.get('tipo') != 'reset_senha':
        return jsonify({"erro": "Token inválido."}), 400

    usuario = Usuario.query.get(int(claims.get('sub')))
    if not usuario or not usuario.ativo:
        return jsonify({"erro": "Conta não encontrada."}), 404

    # Uso único: o chk precisa bater com o senha_hash atual.
    if claims.get('chk') != _chk_senha(usuario.senha_hash):
        return jsonify({"erro": "Este link já foi usado ou expirou. Peça um novo."}), 400

    usuario.senha_hash = generate_password_hash(nova)
    usuario.senha_provisoria = False
    db.session.commit()
    log.info("Senha redefinida via link | id=%s", usuario.id_usuario)
    return jsonify({"mensagem": "Senha redefinida com sucesso. Faça login."}), 200


# Troca de senha autenticado (1º login / voluntária).
@auth_bp.route('/trocar-senha', methods=['POST'])
@jwt_required()
@limiter.limit("10 per 15 minutes")
def trocar_senha():
    dados = request.get_json(silent=True) or {}
    atual = dados.get('senha_atual') or ''
    nova  = dados.get('nova_senha') or ''

    if not nova or len(nova) < 8:
        return jsonify({"erro": "A nova senha deve ter pelo menos 8 caracteres."}), 400

    usuario = Usuario.query.get(int(get_jwt_identity()))
    if not usuario:
        return jsonify({"erro": "Conta não encontrada."}), 404
    if not check_password_hash(usuario.senha_hash, atual):
        return jsonify({"erro": "Senha atual incorreta."}), 401

    usuario.senha_hash = generate_password_hash(nova)
    usuario.senha_provisoria = False
    db.session.commit()
    return jsonify({"mensagem": "Senha alterada com sucesso."}), 200
