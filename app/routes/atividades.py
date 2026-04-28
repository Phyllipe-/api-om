from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, date

from app import db
from app.models import Professor, Aluno, Mapa, Atividade, AtividadeMapa, AtividadeAluno, Usuario, TipoPessoa, LogSessao


def _calcular_periodos(data_ref):
    """Retorna bimestre, trimestre e semestre no formato 'YYYY.N' para uma data."""
    ano = data_ref.year
    mes = data_ref.month
    return {
        "bimestre":  f"{ano}.{(mes - 1) // 2 + 1}",
        "trimestre": f"{ano}.{(mes - 1) // 3 + 1}",
        "semestre":  f"{ano}.{1 if mes <= 6 else 2}",
    }

atividades_bp = Blueprint('atividades', __name__)


def _professor_from_request():
    """Retorna o Professor do usuário logado ou None."""
    id_usuario = get_jwt_identity()
    return Professor.query.filter_by(id_usuario=id_usuario).first()


def _serializar_atividade(at, incluir_detalhes=False):
    prof = Professor.query.get(at.id_professor)
    usr  = Usuario.query.get(prof.id_usuario) if prof else None

    # ── Cálculos de período ──────────────────────────────────────────
    data_inicio = at.data_criacao.date() if at.data_criacao else date.today()
    data_fim    = at.data_finalizacao.date() if at.data_finalizacao else (date.today() if not at.ativo else None)
    dias_duracao = (data_fim - data_inicio).days if data_fim else None

    periodos_inicio = _calcular_periodos(data_inicio)
    periodos_fim    = _calcular_periodos(data_fim) if data_fim else None

    dados = {
        "id_atividade": at.id_atividade,
        "nome":         at.nome,
        "descricao":    at.descricao,
        "ativo":        at.ativo,
        "data_criacao": at.data_criacao.strftime("%Y-%m-%d %H:%M") if at.data_criacao else None,
        "nome_professor": usr.nome_completo if usr else "—",
        "total_mapas":  AtividadeMapa.query.filter_by(id_atividade=at.id_atividade).count(),
        "total_alunos": AtividadeAluno.query.filter_by(id_atividade=at.id_atividade).count(),
        # Período
        "data_previsao_finalizacao": at.data_previsao_finalizacao.strftime("%Y-%m-%d") if at.data_previsao_finalizacao else None,
        "data_finalizacao":          at.data_finalizacao.strftime("%Y-%m-%d %H:%M")    if at.data_finalizacao          else None,
        "dias_duracao": dias_duracao,
        "periodo_inicio": periodos_inicio,
        "periodo_fim":    periodos_fim,
        # Estado
        "finalizada":      at.data_finalizacao is not None,
        "tem_logs":        LogSessao.query.filter_by(id_atividade=at.id_atividade).count() > 0,
        "sequencia_livre": at.sequencia_livre,
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

    # Converte data_previsao_finalizacao se enviada
    data_previsao = None
    if dados.get('data_previsao_finalizacao'):
        try:
            data_previsao = datetime.strptime(dados['data_previsao_finalizacao'], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD."}), 400

    try:
        nova = Atividade(
            nome=dados['nome'],
            descricao=dados.get('descricao', ''),
            id_professor=professor.id_professor,
            data_previsao_finalizacao=data_previsao,
            sequencia_livre=bool(dados.get('sequencia_livre', False)),
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
# ROTA 4: EDITAR ATIVIDADE (somente sem alunos)
# ==========================================
@atividades_bp.route('/<int:id_atividade>', methods=['PATCH'])
@jwt_required()
def editar_atividade(id_atividade):
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    at = Atividade.query.filter_by(
        id_atividade=id_atividade,
        id_professor=professor.id_professor
    ).first()
    if not at:
        return jsonify({"erro": "Atividade não encontrada."}), 404

    dados = request.get_json() or {}

    if dados.get('nome'):
        at.nome = dados['nome']
    if 'descricao' in dados:
        at.descricao = dados.get('descricao') or ''
    if 'data_previsao_finalizacao' in dados:
        if dados['data_previsao_finalizacao']:
            try:
                at.data_previsao_finalizacao = datetime.strptime(dados['data_previsao_finalizacao'], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD."}), 400
        else:
            at.data_previsao_finalizacao = None

    if 'sequencia_livre' in dados:
        at.sequencia_livre = bool(dados['sequencia_livre'])

    if 'mapas' in dados:
        if not dados['mapas']:
            return jsonify({"erro": "A atividade deve ter ao menos um mapa."}), 400
        AtividadeMapa.query.filter_by(id_atividade=id_atividade).delete()
        for item in dados['mapas']:
            db.session.add(AtividadeMapa(
                id_atividade=id_atividade,
                id_mapa=item['id_mapa'],
                ordem=item['ordem'],
            ))

    if 'alunos' in dados:
        AtividadeAluno.query.filter_by(id_atividade=id_atividade).delete()
        for id_aluno in dados['alunos']:
            aluno = Aluno.query.filter_by(
                id_aluno=id_aluno,
                id_professor_responsavel=professor.id_professor
            ).first()
            if aluno:
                db.session.add(AtividadeAluno(
                    id_atividade=id_atividade,
                    id_aluno=id_aluno,
                ))

    db.session.commit()
    return jsonify({"mensagem": "Atividade atualizada.", "id_atividade": id_atividade}), 200


# ==========================================
# ROTA 5: ATIVAR / DESATIVAR ATIVIDADE
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

    # Bloqueia reativação de atividade finalizada
    if not at.ativo and at.data_finalizacao is not None:
        return jsonify({"erro": "Atividade finalizada não pode ser reativada. Use 'Copiar' para criar uma nova."}), 409

    # Bloqueia desativação se houver logs
    if at.ativo:
        tem_logs = LogSessao.query.filter_by(id_atividade=at.id_atividade).count() > 0
        if tem_logs:
            return jsonify({"erro": "Esta atividade possui dados de alunos. Use 'Finalizar' para encerrá-la."}), 409

    at.ativo = not at.ativo
    db.session.commit()
    return jsonify({"id_atividade": id_atividade, "ativo": at.ativo}), 200


# ==========================================
# ROTA 5: FINALIZAR ATIVIDADE
# ==========================================
@atividades_bp.route('/<int:id_atividade>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_atividade(id_atividade):
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    at = Atividade.query.filter_by(
        id_atividade=id_atividade,
        id_professor=professor.id_professor
    ).first()
    if not at:
        return jsonify({"erro": "Atividade não encontrada."}), 404
    if not at.ativo:
        return jsonify({"erro": "A atividade já está inativa."}), 409
    if at.data_finalizacao is not None:
        return jsonify({"erro": "A atividade já foi finalizada."}), 409

    at.ativo = False
    at.data_finalizacao = datetime.utcnow()
    db.session.commit()
    return jsonify({
        "id_atividade": at.id_atividade,
        "ativo": False,
        "data_finalizacao": at.data_finalizacao.strftime("%Y-%m-%d %H:%M"),
    }), 200


# ==========================================
# ROTA 6: COPIAR ATIVIDADE (sem alunos)
# ==========================================
@atividades_bp.route('/<int:id_atividade>/copia', methods=['POST'])
@jwt_required()
def copiar_atividade(id_atividade):
    professor = _professor_from_request()
    if not professor:
        return jsonify({"erro": "Perfil de professor não encontrado."}), 404

    at = Atividade.query.get(id_atividade)
    if not at:
        return jsonify({"erro": "Atividade não encontrada."}), 404

    try:
        nova = Atividade(
            nome=f"{at.nome} (cópia)",
            descricao=at.descricao,
            id_professor=professor.id_professor,
            data_previsao_finalizacao=at.data_previsao_finalizacao,
        )
        db.session.add(nova)
        db.session.flush()

        mapas = (
            AtividadeMapa.query
            .filter_by(id_atividade=at.id_atividade)
            .order_by(AtividadeMapa.ordem)
            .all()
        )
        for am in mapas:
            db.session.add(AtividadeMapa(
                id_atividade=nova.id_atividade,
                id_mapa=am.id_mapa,
                ordem=am.ordem,
            ))

        db.session.commit()
        return jsonify({
            "mensagem": "Atividade copiada com sucesso.",
            "id_atividade": nova.id_atividade,
            "nome": nova.nome,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao copiar atividade: {str(e)}"}), 500


# ==========================================
# ROTA 7: ATIVIDADE ATIVA DE UM ALUNO
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
        if not mapa:
            continue

        # Verifica se o aluno concluiu este mapa nesta atividade
        sessoes = LogSessao.query.filter_by(
            id_aluno=id_aluno,
            id_mapa=mapa.id_mapa,
            id_atividade=atividade.id_atividade
        ).all()
        concluido = any(
            (s.dados_log or {}).get('results', {}).get('clearedMap', False)
            for s in sessoes
        )

        mapas_payload.append({
            "id_mapa":             mapa.id_mapa,
            "ordem":               am.ordem,
            "nome_mapa":           mapa.nome_mapa,
            "caminho_arquivo_xml": mapa.caminho_arquivo_xml,
            "caminho_preview":     mapa.caminho_preview,
            "concluido":           concluido,
        })

    return jsonify({
        "id_atividade":   atividade.id_atividade,
        "nome":           atividade.nome,
        "descricao":      atividade.descricao,
        "sequencia_livre": atividade.sequencia_livre,
        "mapas":          mapas_payload,
    }), 200
