# RINA Trigger API

API FastAPI que consulta os endpoints RINA ACC documentados no projeto `api-itens-acompanhamento/api.http` e retorna itens de acompanhamento cujo titulo ou descricao contenha os termos pesquisados.

## Variaveis de ambiente

Crie um `.env` local a partir de `.env.example`. O `.env` contem credenciais reais e fica fora do Git e do contexto Docker.

```env
USERNAME=seu_usuario
PASSWORD=sua_senha
RINA_BASE_URL=https://api.rinaacc.com.br
```

## Rodando

```bash
uv run uvicorn rina_trigger_api.api:app --reload
```

## Docker

Build:

```bash
docker build -t rina-trigger-api .
```

Execucao local:

```bash
docker run --rm -p 8000:8000 --env-file .env rina-trigger-api
```

Healthcheck:

```http
GET /health
```

Endpoint principal:

```http
GET /trigger-items
```

Filtros opcionais:

- `initial_date`: data inicial da auditoria/publicacao, por exemplo `2026-05-01`
- `final_date`: data final da auditoria/publicacao, por exemplo `2026-05-15`
- `term`: termo pesquisado no titulo ou descricao. Pode ser repetido, por exemplo `?term=HISL&term=vane`. Quando omitido, usa `trigger`, `gatilho` e `gatinho`.

Resposta:

```json
[
  {
    "audit_date": "10/05/2026",
    "aircraft_prefix": "PT-ABC",
    "operator": "Operadora",
    "title": "Trigger item",
    "description": "Descricao do item de acompanhamento",
    "resolved": false
  }
]
```

## Testes

```bash
uv run --extra dev pytest
```

O projeto exige no minimo 90% de cobertura via `pytest-cov`.

O teste e2e real usa `USERNAME`, `PASSWORD` e `RINA_BASE_URL` do ambiente ou `.env`. Por padrao ele busca `HISL` entre `2026-05-01` e `2026-05-18`; esses valores podem ser alterados com `E2E_SEARCH_TERM`, `E2E_INITIAL_DATE` e `E2E_FINAL_DATE`.
