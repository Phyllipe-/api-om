from app import db
from datetime import datetime

# -----------------------------------------
# TABELAS DE AUTENTICAÇÃO E PERFIS
# -----------------------------------------
class TipoPessoa(db.Model):
    __tablename__ = 'tipo_pessoa'
    id_tipo = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(50), nullable=False)

class Usuario(db.Model):
    __tablename__ = 'usuario'
    id_usuario = db.Column(db.Integer, primary_key=True)
    id_tipo = db.Column(db.Integer, db.ForeignKey('tipo_pessoa.id_tipo'), nullable=False)
    nome_completo = db.Column(db.String(150), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Professor(db.Model):
    __tablename__ = 'professor'
    id_professor = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), unique=True, nullable=False)
    registro_profissional = db.Column(db.String(50), nullable=True)

class Aluno(db.Model):
    __tablename__ = 'aluno'
    id_aluno = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), unique=True, nullable=False)
    id_professor_responsavel = db.Column(db.Integer, db.ForeignKey('professor.id_professor'), nullable=False)
    escolaridade = db.Column(db.String(100), nullable=True)
    login = db.Column(db.String(80), unique=True, nullable=True)  # identificador curto; padrão = parte antes do '@'

# -----------------------------------------
# TABELAS DE OPERAÇÃO E LOGS (REFERÊNCIAS)
# -----------------------------------------
class Mapa(db.Model):
    __tablename__ = 'mapa'
    id_mapa = db.Column(db.Integer, primary_key=True)
    nome_mapa = db.Column(db.String(150), nullable=False)
    id_criador = db.Column(db.Integer, db.ForeignKey('professor.id_professor'), nullable=False)
    caminho_arquivo_xml = db.Column(db.String(500), nullable=False) # URL ou path do arquivo XML
    caminho_preview     = db.Column(db.String(500), nullable=True)  # thumbnail PNG
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True, nullable=False, server_default='true')

class LogSessao(db.Model):
    __tablename__ = 'log_sessao'
    id_log = db.Column(db.Integer, primary_key=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey('aluno.id_aluno'), nullable=False)
    id_criador = db.Column(db.Integer, db.ForeignKey('professor.id_professor'), nullable=False)
    id_mapa = db.Column(db.Integer, db.ForeignKey('mapa.id_mapa'), nullable=False)
    caminho_arquivo_log = db.Column(db.String(500), nullable=False) # Rota onde o CSV/JSON de passos está guardado
    data_criacao_arquivo_log = db.Column(db.DateTime, default=datetime.utcnow)

# -----------------------------------------
# TABELAS DE ANÁLISE DE OM
# -----------------------------------------
class Lateralidade(db.Model):
    __tablename__ = 'lateralidade'
    id_lateralidade = db.Column(db.Integer, primary_key=True)
    id_log = db.Column(db.Integer, db.ForeignKey('log_sessao.id_log'), unique=True, nullable=False)
    caminho_arquivo_json = db.Column(db.String(500), nullable=False)

class SimulacaoTrajetoria(db.Model):
    __tablename__ = 'simulacao_trajetoria'
    id_simulacao = db.Column(db.Integer, primary_key=True)
    id_log = db.Column(db.Integer, db.ForeignKey('log_sessao.id_log'), unique=True, nullable=False)
    caminho_arquivo_json = db.Column(db.String(500), nullable=False)

class Trafego(db.Model):
    __tablename__ = 'trafego'
    id_trafego = db.Column(db.Integer, primary_key=True)
    id_log = db.Column(db.Integer, db.ForeignKey('log_sessao.id_log'), unique=True, nullable=False)
    caminho_arquivo_json = db.Column(db.String(500), nullable=False)

class Giros(db.Model):
    __tablename__ = 'giros'
    id_giros = db.Column(db.Integer, primary_key=True)
    id_log = db.Column(db.Integer, db.ForeignKey('log_sessao.id_log'), unique=True, nullable=False)
    caminho_arquivo_json = db.Column(db.String(500), nullable=False)

class Comparacao(db.Model):
    __tablename__ = 'comparacao'
    id_comparacao = db.Column(db.Integer, primary_key=True)
    id_log = db.Column(db.Integer, db.ForeignKey('log_sessao.id_log'), unique=True, nullable=False)
    caminho_arquivo_json = db.Column(db.String(500), nullable=False)

class Atividade(db.Model):
    __tablename__ = 'atividade'
    id_atividade = db.Column(db.Integer, primary_key=True)
    nome         = db.Column(db.String(150), nullable=False)
    descricao    = db.Column(db.Text, nullable=True)
    id_professor = db.Column(db.Integer, db.ForeignKey('professor.id_professor'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo        = db.Column(db.Boolean, default=True, nullable=False)

class AtividadeMapa(db.Model):
    __tablename__ = 'atividade_mapa'
    id           = db.Column(db.Integer, primary_key=True)
    id_atividade = db.Column(db.Integer, db.ForeignKey('atividade.id_atividade'), nullable=False)
    id_mapa      = db.Column(db.Integer, db.ForeignKey('mapa.id_mapa'), nullable=False)
    ordem        = db.Column(db.Integer, nullable=False)

class AtividadeAluno(db.Model):
    __tablename__ = 'atividade_aluno'
    id               = db.Column(db.Integer, primary_key=True)
    id_atividade     = db.Column(db.Integer, db.ForeignKey('atividade.id_atividade'), nullable=False)
    id_aluno         = db.Column(db.Integer, db.ForeignKey('aluno.id_aluno'), nullable=False)
    data_atribuicao  = db.Column(db.DateTime, default=datetime.utcnow)