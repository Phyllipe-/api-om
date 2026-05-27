ALUNO_BASE = {
    "nome_completo": "Aluno Teste",
    "data_nascimento": "2010-04-10",
    "email": "aluno@teste.com",
    "senha": "senha123",
}


class TestListarAlunos:
    def test_lista_vazia_autenticado(self, client, auth_headers):
        resp = client.get("/api/alunos/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "alunos" in data
        assert isinstance(data["alunos"], list)

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/api/alunos/")
        assert resp.status_code == 401


class TestCadastrarAluno:
    def test_cadastro_sucesso(self, client, auth_headers):
        resp = client.post("/api/alunos/", headers=auth_headers, json=ALUNO_BASE)
        assert resp.status_code in (200, 201)

    def test_cadastro_email_duplicado(self, client, auth_headers):
        client.post("/api/alunos/", headers=auth_headers, json=ALUNO_BASE)
        resp = client.post("/api/alunos/", headers=auth_headers, json=ALUNO_BASE)
        assert resp.status_code == 409

    def test_cadastro_campo_obrigatorio_faltando(self, client, auth_headers):
        resp = client.post("/api/alunos/", headers=auth_headers, json={"nome_completo": "Incompleto"})
        assert resp.status_code == 400

    def test_cadastro_sem_token(self, client):
        resp = client.post("/api/alunos/", json=ALUNO_BASE)
        assert resp.status_code == 401


class TestDetalheAluno:
    def test_aluno_nao_encontrado(self, client, auth_headers):
        resp = client.get("/api/alunos/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_detalhe_aluno_cadastrado(self, client, auth_headers):
        criar = client.post("/api/alunos/", headers=auth_headers, json=ALUNO_BASE)
        id_aluno = criar.get_json().get("id_aluno")
        if id_aluno:
            resp = client.get(f"/api/alunos/{id_aluno}", headers=auth_headers)
            assert resp.status_code == 200
