from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from datetime import datetime

from app import db
from app.models import Usuario, Professor, TipoPessoa

auth_bp = Blueprint('auth', __name__)


# ==========================================
# ROTA 1: LOGIN E GERAÇÃO DE TOKEN JWT
# ==========================================
@auth_bp.route('/login', methods=['POST'])
def login():
    dados = request.get_json(silent=True) or request.form
    if not dados or 'email' not in dados or 'senha' not in dados:
        return jsonify({"erro": "Email e senha são obrigatórios."}), 400

    usuario = Usuario.query.filter_by(email=dados['email']).first()
    if not usuario or not check_password_hash(usuario.senha_hash, dados['senha']):
        return jsonify({"erro": "Email ou senha incorretos."}), 401
        
    if not usuario.ativo:
        return jsonify({"erro": "Esta conta está desativada."}), 403

    token_de_acesso = create_access_token(
        identity=str(usuario.id_usuario), 
        additional_claims={
            "id_tipo": usuario.id_tipo,
            "nome": usuario.nome_completo
        }
    )

    return jsonify({
        "mensagem": "Login realizado com sucesso!", 
        "token": token_de_acesso, 
        "usuario": {
            "id_usuario": usuario.id_usuario, 
            "id_tipo": usuario.id_tipo, 
            "nome": usuario.nome_completo
        }
    }), 200
    
    
# ==========================================
# ROTA 2: CADASTRO DE PROFESSOR 
# ==========================================
@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register_professor():
    # Restrito ao professor administrador (id_usuario = 1)
    if int(get_jwt_identity()) != 1:
        return jsonify({"erro": "Apenas o administrador pode cadastrar novos professores."}), 403

    dados = request.get_json()
    campos_obrigatorios = ['nome_completo', 'data_nascimento', 'email', 'senha']
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"O campo {campo} é obrigatório."}), 400

    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({"erro": "Este email já está cadastrado."}), 409

    try:
        tipo_prof = TipoPessoa.query.filter_by(descricao="Professor").first()
        senha_criptografada = generate_password_hash(dados['senha'])
        data_nasc = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()

        novo_usuario = Usuario(
            id_tipo=tipo_prof.id_tipo,
            nome_completo=dados['nome_completo'],
            data_nascimento=data_nasc,
            email=dados['email'],
            senha_hash=senha_criptografada
        )
        db.session.add(novo_usuario)
        db.session.flush()

        registro = dados.get('registro_profissional', '')
        novo_professor = Professor(id_usuario=novo_usuario.id_usuario, registro_profissional=registro)
        
        db.session.add(novo_professor)
        db.session.commit()

        return jsonify({"mensagem": "Professor cadastrado com sucesso!"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Falha no cadastro: {str(e)}"}), 500