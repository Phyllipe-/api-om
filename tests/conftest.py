import os
import pytest

# Patch JSONB → JSON antes de importar os models (JSONB não existe no SQLite)
from sqlalchemy.types import JSON
import sqlalchemy.dialects.postgresql as pg_types
pg_types.JSONB = JSON

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-apenas-para-testes'
os.environ['ALLOWED_ORIGINS'] = 'http://localhost:3000'
os.environ['FLASK_ENV'] = 'testing'
os.environ['REGISTRO_PUBLICO'] = 'false'

from app import create_app, db as _db
from app.models import TipoPessoa, Usuario, Professor
from werkzeug.security import generate_password_hash
from datetime import date


@pytest.fixture(scope='session')
def app():
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    with flask_app.app_context():
        _db.create_all()
        _db.session.add(TipoPessoa(descricao='Professor'))
        _db.session.add(TipoPessoa(descricao='Aluno'))
        _db.session.commit()
        yield flask_app
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function', autouse=True)
def limpar_usuarios(app):
    yield
    with app.app_context():
        Professor.query.delete()
        Usuario.query.delete()
        _db.session.commit()


@pytest.fixture
def professor(app):
    """Cria um professor de teste e retorna (usuario, senha_plain)."""
    with app.app_context():
        tipo = TipoPessoa.query.filter_by(descricao='Professor').first()
        u = Usuario(
            id_tipo=tipo.id_tipo,
            nome_completo='Prof Teste',
            data_nascimento=date(1990, 1, 1),
            email='prof@teste.com',
            senha_hash=generate_password_hash('senha123'),
        )
        _db.session.add(u)
        _db.session.flush()
        _db.session.add(Professor(id_usuario=u.id_usuario))
        _db.session.commit()
        return u.id_usuario, 'prof@teste.com', 'senha123'
