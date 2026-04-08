# Scripts

Organização por responsabilidade. Todos devem ser executados a partir da raiz do projeto:

```
python scripts/<pasta>/<script>.py
```

---

## `sistema/` — Estrutura e migrações de schema

| Script | Quando usar |
|---|---|
| `init_db.py` | Primeira vez — cria tabelas e o usuário admin inicial |
| `migrate.py` | Sempre que houver alteração de schema — idempotente, seguro re-executar |

**Ordem recomendada na primeira instalação:**
```
python scripts/sistema/init_db.py
python scripts/sistema/migrate.py
```

**Convenção para novas migrações:** adicionar uma nova seção `M00X` em `migrate.py` seguindo o padrão existente (verificação antes do ALTER, `ok()`/`skip()` de retorno).

---

## `demo/` — Dados de demonstração

| Script | Quando usar |
|---|---|
| `seed_demo.py` | Gera professores, alunos, mapas, sessões e análises fictícias para testes |

```
python scripts/demo/seed_demo.py          # popula
python scripts/demo/seed_demo.py --limpar # remove tudo antes de popular
```

---

## `manutencao/` — Operações destrutivas

| Script | Quando usar |
|---|---|
| `limpar_db.py` | Remove todos os dados exceto `id_usuario = 1` |

```
python scripts/manutencao/limpar_db.py             # pede confirmação
python scripts/manutencao/limpar_db.py --confirmar # sem prompt
```
