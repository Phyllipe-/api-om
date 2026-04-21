from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

from app import db
from app.models import Usuario, Professor, Aluno, TipoPessoa

alunos_bp = Blueprint('alunos', __name__)


def _login_efetivo(aluno, usr):
    return aluno.login or usr.email.split('@')[0]


def _aluno_dict(aluno, usr):
    hoje = datetime.now().date()
    idade = hoje.year - usr.data_nascimento.year - (
        (hoje.month, hoje.day) < (usr.data_nascimento.month, usr.data_nascimento.day)
    )
    return {
        "id_aluno": aluno.id_aluno,
        "nome_completo": usr.nome_completo,
        "email": usr.email,
        "login": _login_efetivo(aluno, usr),
        "idade": idade,
        "data_nascimento": usr.data_nascimento.strftime('%Y-%m-%d') if usr.data_nascimento else None,
        "escolaridade": aluno.escolaridade,
        "telefone":   aluno.telefone,
        "cep":        aluno.cep,
        "logradouro": aluno.logradouro,
        "ativo": usr.ativo
    }


# ==========================================
# ROTA 1: CADASTRAR UM NOVO ALUNO
# ==========================================
@alunos_bp.route('/', methods=['POST'])
@jwt_required()
def cadastrar_aluno():
    id_usuario_logado = get_jwt_identity()
    claims = get_jwt()

    tipo_prof = TipoPessoa.query.filter_by(descricao="Professor").first()
    if claims.get('id_tipo') != tipo_prof.id_tipo:
        return jsonify({"erro": "Apenas professores podem cadastrar alunos."}), 403

    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    dados = request.get_json()
    for campo in ['nome_completo', 'data_nascimento', 'email', 'senha']:
        if campo not in dados:
            return jsonify({"erro": f"O campo {campo} é obrigatório."}), 400

    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({"erro": "Já existe um utilizador com este email."}), 409

    login = (dados.get('login') or '').strip() or dados['email'].split('@')[0]
    if Aluno.query.filter_by(login=login).first():
        return jsonify({"erro": "Já existe um aluno com este login."}), 409

    try:
        tipo_aluno = TipoPessoa.query.filter_by(descricao="Aluno").first()
        data_nasc = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()

        novo_usuario = Usuario(
            id_tipo=tipo_aluno.id_tipo,
            nome_completo=dados['nome_completo'],
            data_nascimento=data_nasc,
            email=dados['email'],
            senha_hash=generate_password_hash(dados['senha'])
        )
        db.session.add(novo_usuario)
        db.session.flush()

        novo_aluno = Aluno(
            id_usuario=novo_usuario.id_usuario,
            id_professor_responsavel=professor.id_professor,
            escolaridade=dados.get('escolaridade', ''),
            login=login,
            telefone=dados.get('telefone') or None,
            cep=dados.get('cep') or None,
            logradouro=dados.get('logradouro') or None,
        )
        db.session.add(novo_aluno)
        db.session.commit()

        return jsonify({"mensagem": "Aluno cadastrado e vinculado ao professor com sucesso!"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao cadastrar aluno: {str(e)}"}), 500


# ==========================================
# ROTA 2: LISTAR ALUNOS DO PROFESSOR
# ==========================================
@alunos_bp.route('/', methods=['GET'])
@jwt_required()
def listar_alunos():
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    alunos = Aluno.query.filter_by(id_professor_responsavel=professor.id_professor).all()
    lista = [_aluno_dict(a, Usuario.query.get(a.id_usuario)) for a in alunos]
    return jsonify({"total": len(lista), "alunos": lista}), 200


# ==========================================
# ROTA 3: ATIVAR / DESATIVAR ALUNO
# ==========================================
@alunos_bp.route('/<int:id_aluno>/ativo', methods=['PATCH'])
@jwt_required()
def toggle_ativo(id_aluno):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    aluno = Aluno.query.filter_by(id_aluno=id_aluno, id_professor_responsavel=professor.id_professor).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado ou sem permissão."}), 404

    usr = Usuario.query.get(aluno.id_usuario)
    usr.ativo = not usr.ativo
    db.session.commit()
    return jsonify({"id_aluno": id_aluno, "ativo": usr.ativo}), 200


# ==========================================
# ROTA 4: DETALHE DE UM ALUNO
# ==========================================
@alunos_bp.route('/<int:id_aluno>', methods=['GET'])
@jwt_required()
def detalhar_aluno(id_aluno):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    aluno = Aluno.query.filter_by(id_aluno=id_aluno, id_professor_responsavel=professor.id_professor).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado."}), 404

    usr = Usuario.query.get(aluno.id_usuario)
    return jsonify(_aluno_dict(aluno, usr)), 200


# ==========================================
# ROTA 5: BUSCAR ALUNO POR EMAIL OU LOGIN
# ==========================================
@alunos_bp.route('/buscar', methods=['GET'])
@jwt_required()
def buscar_aluno():
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"erro": "Parâmetro 'q' é obrigatório."}), 400

    if '@' in q:
        usr = Usuario.query.filter(db.func.lower(Usuario.email) == q.lower()).first()
        aluno = Aluno.query.filter_by(
            id_usuario=usr.id_usuario if usr else None,
            id_professor_responsavel=professor.id_professor
        ).first() if usr else None
    else:
        aluno = Aluno.query.filter(
            db.func.lower(Aluno.login) == q.lower(),
            Aluno.id_professor_responsavel == professor.id_professor
        ).first()
        usr = Usuario.query.get(aluno.id_usuario) if aluno else None

    if not aluno or not usr:
        return jsonify({"erro": "Nenhum aluno encontrado."}), 404

    return jsonify(_aluno_dict(aluno, usr)), 200


# ==========================================
# ROTA 5b: BUSCA GLOBAL DE ALUNOS (todos os professores)
# Admin vê todos; professor vê apenas os seus.
# ==========================================
@alunos_bp.route('/buscar-todos', methods=['GET'])
@jwt_required()
def buscar_todos():
    id_usuario_logado = int(get_jwt_identity())
    q = request.args.get('q', '').strip().lower()

    # Determina o professor atual (para calcular is_meu)
    professor_atual = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    id_prof_atual = professor_atual.id_professor if professor_atual else None

    # Com busca: todos os alunos do sistema; sem busca: só os próprios (admin vê todos)
    if q or id_usuario_logado == 1:
        alunos = Aluno.query.all()
    else:
        if not professor_atual:
            return jsonify({"erro": "Perfil de professor não encontrado."}), 404
        alunos = Aluno.query.filter_by(id_professor_responsavel=id_prof_atual).all()

    resultado = []
    for aluno in alunos:
        usr = Usuario.query.get(aluno.id_usuario)
        if not usr:
            continue
        # Filtra por nome, login ou email (se q fornecido)
        if q:
            campos = [
                usr.nome_completo.lower(),
                (aluno.login or "").lower(),
                usr.email.lower(),
            ]
            if not any(q in c for c in campos):
                continue

        prof = Professor.query.get(aluno.id_professor_responsavel)
        prof_usr = Usuario.query.get(prof.id_usuario) if prof else None

        hoje = datetime.now().date()
        idade = hoje.year - usr.data_nascimento.year - (
            (hoje.month, hoje.day) < (usr.data_nascimento.month, usr.data_nascimento.day)
        ) if usr.data_nascimento else None

        resultado.append({
            "id_aluno":      aluno.id_aluno,
            "nome_completo": usr.nome_completo,
            "email":         usr.email,
            "login":         aluno.login or usr.email.split('@')[0],
            "escolaridade":  aluno.escolaridade,
            "ativo":         usr.ativo,
            "idade":         idade,
            "professor":     prof_usr.nome_completo if prof_usr else "—",
            "id_professor":  aluno.id_professor_responsavel,
            "is_meu":        aluno.id_professor_responsavel == id_prof_atual,
        })

    resultado.sort(key=lambda x: x["nome_completo"].lower())
    return jsonify({"total": len(resultado), "alunos": resultado}), 200


# ==========================================
# ROTA 5c: APROPRIAR ALUNO (transferir para o professor logado)
# Só permitido para alunos inativos de outro professor.
# ==========================================
@alunos_bp.route('/<int:id_aluno>/apropriar', methods=['POST'])
@jwt_required()
def apropriar_aluno(id_aluno):
    id_usuario_logado = int(get_jwt_identity())
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    aluno = Aluno.query.get(id_aluno)
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado."}), 404

    usr = Usuario.query.get(aluno.id_usuario)
    if not usr:
        return jsonify({"erro": "Usuário do aluno não encontrado."}), 404

    if usr.ativo:
        return jsonify({"erro": "Apenas alunos inativos podem ser apropriados."}), 400

    if aluno.id_professor_responsavel == professor.id_professor:
        return jsonify({"erro": "Este aluno já pertence a você."}), 400

    aluno.id_professor_responsavel = professor.id_professor
    db.session.commit()
    return jsonify({"id_aluno": id_aluno, "id_professor": professor.id_professor}), 200


# ==========================================
# ROTA 5d: VERIFICAR DISPONIBILIDADE DE LOGIN
# ==========================================
@alunos_bp.route('/check-login', methods=['GET'])
@jwt_required()
def check_login():
    login = request.args.get('login', '').strip()
    exclude_id = request.args.get('exclude_id', type=int)
    if not login:
        return jsonify({"erro": "Parâmetro 'login' é obrigatório."}), 400

    q = Aluno.query.filter(Aluno.login == login)
    if exclude_id:
        q = q.filter(Aluno.id_aluno != exclude_id)
    disponivel = q.first() is None
    return jsonify({"disponivel": disponivel}), 200


# ==========================================
# ROTA 6: EDITAR DADOS DO ALUNO
# ==========================================
@alunos_bp.route('/<int:id_aluno>', methods=['PATCH'])
@jwt_required()
def editar_aluno(id_aluno):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    aluno = Aluno.query.filter_by(id_aluno=id_aluno, id_professor_responsavel=professor.id_professor).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado ou sem permissão."}), 404

    dados = request.get_json()
    usr = Usuario.query.get(aluno.id_usuario)

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

    if 'escolaridade' in dados:
        aluno.escolaridade = dados['escolaridade']

    if 'telefone' in dados:
        aluno.telefone = dados['telefone'] or None
    if 'cep' in dados:
        aluno.cep = dados['cep'] or None
    if 'logradouro' in dados:
        aluno.logradouro = dados['logradouro'] or None

    if 'nova_senha' in dados and dados['nova_senha']:
        from werkzeug.security import generate_password_hash
        usr.senha_hash = generate_password_hash(dados['nova_senha'])

    db.session.commit()
    return jsonify(_aluno_dict(aluno, usr)), 200


# ==========================================
# ROTA 7: ATUALIZAR LOGIN DO ALUNO
# ==========================================
@alunos_bp.route('/<int:id_aluno>/login', methods=['PATCH'])
@jwt_required()
def atualizar_login(id_aluno):
    id_usuario_logado = get_jwt_identity()
    professor = Professor.query.filter_by(id_usuario=id_usuario_logado).first()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    aluno = Aluno.query.filter_by(id_aluno=id_aluno, id_professor_responsavel=professor.id_professor).first()
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado ou sem permissão."}), 404

    dados = request.get_json()
    novo_login = (dados.get('login') or '').strip()
    if not novo_login:
        return jsonify({"erro": "O campo 'login' é obrigatório."}), 400

    existente = Aluno.query.filter(Aluno.login == novo_login, Aluno.id_aluno != id_aluno).first()
    if existente:
        return jsonify({"erro": "Este login já está em uso por outro aluno."}), 409

    aluno.login = novo_login
    db.session.commit()
    return jsonify({"id_aluno": id_aluno, "login": novo_login}), 200
