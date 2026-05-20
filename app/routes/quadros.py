from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Quadro, PreferenciaQuadro, Professor, Usuario

quadros_bp = Blueprint('quadros', __name__)


def _quadro_dict(q):
    return {
        "id":                     q.id,
        "chave":                  q.chave,
        "nome":                   q.nome,
        "secao":                  q.secao,
        "tamanho":                q.tamanho,
        "ordem_padrao":           q.ordem_padrao,
        "ativo_padrao":           q.ativo_padrao,
        "personalizavel":         q.personalizavel,
        "exclusivo_sessao_unica": q.exclusivo_sessao_unica,
    }


def _is_admin(id_usuario):
    try:
        return int(id_usuario) == 1
    except (TypeError, ValueError):
        return False


# ── Catálogo ──────────────────────────────────────────────────────────────────

@quadros_bp.route('/', methods=['GET'])
@jwt_required()
def listar_quadros():
    """Lista todos os quadros do catálogo (qualquer usuário autenticado)."""
    quadros = Quadro.query.order_by(Quadro.secao, Quadro.ordem_padrao).all()
    return jsonify([_quadro_dict(q) for q in quadros]), 200


@quadros_bp.route('/<int:id_quadro>', methods=['PATCH'])
@jwt_required()
def editar_quadro(id_quadro):
    """Edita nome, ativo_padrao e personalizavel (somente admin)."""
    id_usuario = get_jwt_identity()
    if not _is_admin(id_usuario):
        return jsonify({"erro": "Acesso restrito ao administrador."}), 403

    quadro = Quadro.query.get(id_quadro)
    if not quadro:
        return jsonify({"erro": "Quadro não encontrado."}), 404

    dados = request.get_json() or {}

    if 'nome' in dados:
        nome = dados['nome'].strip()
        if not nome:
            return jsonify({"erro": "Nome não pode ser vazio."}), 400
        quadro.nome = nome

    if 'ativo_padrao' in dados:
        quadro.ativo_padrao = bool(dados['ativo_padrao'])

    if 'personalizavel' in dados:
        quadro.personalizavel = bool(dados['personalizavel'])

    if 'exclusivo_sessao_unica' in dados:
        quadro.exclusivo_sessao_unica = bool(dados['exclusivo_sessao_unica'])

    db.session.commit()
    return jsonify(_quadro_dict(quadro)), 200


# ── Preferências do professor ─────────────────────────────────────────────────

@quadros_bp.route('/preferencias/', methods=['GET'])
@jwt_required()
def get_preferencias():
    """
    Retorna as preferências do usuário logado.
    Para quadros sem preferência salva, retorna os valores padrão do catálogo.
    """
    id_usuario = int(get_jwt_identity())
    todos = Quadro.query.order_by(Quadro.secao, Quadro.ordem_padrao).all()
    prefs = {
        p.chave_quadro: p
        for p in PreferenciaQuadro.query.filter_by(id_usuario=id_usuario).all()
    }

    resultado = []
    for q in todos:
        p = prefs.get(q.chave)
        resultado.append({
            "chave":                  q.chave,
            "nome":                   q.nome,
            "secao":                  q.secao,
            "tamanho":                q.tamanho,
            "ordem_padrao":           q.ordem_padrao,
            "ativo_padrao":           q.ativo_padrao,
            "personalizavel":         q.personalizavel,
            "exclusivo_sessao_unica": q.exclusivo_sessao_unica,
            "visivel":                p.visivel if p else q.ativo_padrao,
            "ordem":                  p.ordem   if p else q.ordem_padrao,
        })

    return jsonify(resultado), 200


@quadros_bp.route('/preferencias/', methods=['PATCH'])
@jwt_required()
def salvar_preferencias():
    """
    Salva preferências do usuário logado.
    Body: [{ "chave": "mapa-giros", "visivel": true, "ordem": 1 }, ...]
    """
    id_usuario = int(get_jwt_identity())
    dados = request.get_json() or []

    if not isinstance(dados, list):
        return jsonify({"erro": "Body deve ser uma lista de preferências."}), 400

    chaves_validas = {q.chave for q in Quadro.query.filter_by(personalizavel=True).all()}

    for item in dados:
        chave = item.get('chave')
        if not chave or chave not in chaves_validas:
            continue

        pref = PreferenciaQuadro.query.filter_by(
            id_usuario=id_usuario, chave_quadro=chave
        ).first()

        if pref is None:
            pref = PreferenciaQuadro(id_usuario=id_usuario, chave_quadro=chave)
            db.session.add(pref)

        if 'visivel' in item:
            pref.visivel = bool(item['visivel'])
        if 'ordem' in item:
            pref.ordem = item['ordem']

    db.session.commit()
    return jsonify({"ok": True}), 200
