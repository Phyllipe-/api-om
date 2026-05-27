ATIVIDADE_BASE = {
    "nome": "Atividade Teste",
    "descricao": "Descrição de teste",
}


class TestListarAtividades:
    def test_lista_autenticado(self, client, auth_headers):
        resp = client.get("/api/atividades/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "atividades" in data

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/api/atividades/")
        assert resp.status_code == 401


class TestCriarAtividade:
    def test_criar_sucesso(self, client, auth_headers):
        resp = client.post("/api/atividades/", headers=auth_headers, json=ATIVIDADE_BASE)
        assert resp.status_code in (200, 201)

    def test_criar_com_sequencia_livre(self, client, auth_headers):
        resp = client.post("/api/atividades/", headers=auth_headers, json={
            **ATIVIDADE_BASE,
            "sequencia_livre": True,
        })
        assert resp.status_code in (200, 201)

    def test_criar_sem_nome_retorna_400(self, client, auth_headers):
        resp = client.post("/api/atividades/", headers=auth_headers, json={"descricao": "sem nome"})
        assert resp.status_code == 400

    def test_criar_sem_token_retorna_401(self, client):
        resp = client.post("/api/atividades/", json=ATIVIDADE_BASE)
        assert resp.status_code == 401


class TestToggleAtividade:
    def test_toggle_ativo(self, client, auth_headers):
        criar = client.post("/api/atividades/", headers=auth_headers, json=ATIVIDADE_BASE)
        data = criar.get_json()
        id_at = data.get("id_atividade")
        if id_at:
            resp = client.patch(f"/api/atividades/{id_at}/ativo", headers=auth_headers)
            assert resp.status_code == 200
