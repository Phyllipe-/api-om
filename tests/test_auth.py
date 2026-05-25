import pytest


class TestCheckEmail:
    def test_email_disponivel(self, client):
        resp = client.get('/api/auth/check-email?email=novo@teste.com')
        assert resp.status_code == 200
        assert resp.get_json()['disponivel'] is True

    def test_email_ocupado(self, client, professor):
        _, email, _ = professor
        resp = client.get(f'/api/auth/check-email?email={email}')
        assert resp.status_code == 200
        assert resp.get_json()['disponivel'] is False

    def test_sem_parametro_email(self, client):
        resp = client.get('/api/auth/check-email')
        assert resp.status_code == 400


class TestLogin:
    def test_campos_obrigatorios(self, client):
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 400

    def test_credenciais_invalidas(self, client):
        resp = client.post('/api/auth/login', json={
            'email': 'naoexiste@teste.com',
            'senha': 'qualquer'
        })
        assert resp.status_code == 401
        assert 'erro' in resp.get_json()

    def test_senha_errada(self, client, professor):
        _, email, _ = professor
        resp = client.post('/api/auth/login', json={
            'email': email,
            'senha': 'senhaerrada'
        })
        assert resp.status_code == 401

    def test_login_valido(self, client, professor):
        _, email, senha = professor
        resp = client.post('/api/auth/login', json={
            'email': email,
            'senha': senha
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['usuario']['nome'] == 'Prof Teste'

    def test_usuario_inativo(self, client, app, professor):
        from app import db
        from app.models import Usuario
        id_usuario, email, senha = professor
        with app.app_context():
            u = db.session.get(Usuario, id_usuario)
            u.ativo = False
            db.session.commit()

        resp = client.post('/api/auth/login', json={
            'email': email,
            'senha': senha
        })
        assert resp.status_code == 403


class TestRegisterPublic:
    def test_registro_publico_desabilitado(self, client):
        resp = client.post('/api/auth/register-public', json={
            'nome_completo': 'Prof Pub',
            'data_nascimento': '1990-01-01',
            'email': 'pub@teste.com',
            'senha': 'senha123'
        })
        assert resp.status_code == 403
        assert 'desabilitado' in resp.get_json()['erro']
