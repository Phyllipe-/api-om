class TestMapas:
    def test_listar_mapas_autenticado(self, client, auth_headers):
        resp = client.get("/api/treinos/mapas", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "mapas" in data or isinstance(data, list)

    def test_listar_meus_mapas(self, client, auth_headers):
        resp = client.get("/api/treinos/mapas/meus", headers=auth_headers)
        assert resp.status_code == 200

    def test_listar_mapas_sem_token(self, client):
        resp = client.get("/api/treinos/mapas")
        assert resp.status_code == 401


class TestSessoes:
    def test_sessoes_sem_param_retorna_erro(self, client, auth_headers):
        resp = client.get("/api/treinos/sessoes", headers=auth_headers)
        assert resp.status_code in (400, 422)

    def test_sessoes_aluno_inexistente(self, client, auth_headers):
        resp = client.get("/api/treinos/sessoes?id_aluno=9999", headers=auth_headers)
        assert resp.status_code in (200, 404)

    def test_sessoes_sem_token(self, client):
        resp = client.get("/api/treinos/sessoes?id_aluno=1")
        assert resp.status_code == 401
