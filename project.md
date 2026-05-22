# Consulta de itens de acompanhamento

Este documento registra o fluxo usado neste projeto para consultar itens de
acompanhamento do RINA ACC e encaminhar os dados para analise.

## Resumo do fluxo

1. Fazer login para obter o token.
2. Consultar as auditorias do periodo.
3. Consultar o relatorio de cada auditoria com `GET /report/{audit_id}`.
4. Ler os IDs de acompanhamento no relatorio:
   `_accompaniment` para atuais e `_accompanimentPrevious` para anteriores.
5. Para cada ID de item, consultar
   `GET /accompanimentReport/{accompaniment_id}`.
6. Juntar o payload do item com o contexto da auditoria e do relatorio.

## Autenticacao

```http
POST https://api.rinaacc.com.br/login
Content-Type: application/json

{
  "login": "usuario",
  "password": "senha"
}
```

O token retornado em `body.token` deve ser enviado no header `Authorization`:

```http
Authorization: {token}
```

## Rotas usadas

### Buscar auditorias

```http
POST https://api.rinaacc.com.br/search
Content-Type: application/json
Authorization: {token}
```

O corpo da busca define periodo, bases, operadoras, aeronaves e tipos de
auditoria. O retorno fornece o `_id` de cada auditoria.

### Consultar o relatorio da auditoria

```http
GET https://api.rinaacc.com.br/report/{audit_id}
Authorization: {token}
```

O relatorio traz os IDs de acompanhamento:

```json
{
  "_id": "audit-id",
  "_accompaniment": ["current-accompaniment-id"],
  "_accompanimentPrevious": ["previous-accompaniment-id"]
}
```

Para itens atuais, usar os IDs de `_accompaniment`. Para itens anteriores, os
testes deste projeto indicaram que os IDs de `_accompanimentPrevious` tambem
respondem na rota `accompanimentReport`.

### Consultar um item de acompanhamento

```http
GET https://api.rinaacc.com.br/accompanimentReport/{accompaniment_id}
Authorization: {token}
```

`accompaniment_id` e o ID do item vindo de `_accompaniment` ou
`_accompanimentPrevious`. Nao usar o `audit_id` nessa rota. Nos testes deste
projeto, passar o ID da auditoria para `accompanimentReport` retornou HTTP 500.

Exemplo de campos retornados:

```json
{
  "_id": "accompaniment-id",
  "_accreport": "audit-id",
  "title": "PBO ACIMA DO CONTRATADO.",
  "description": "Descricao do item.",
  "insertDate": "2025-01-01T03:00:00.000Z",
  "solutionDate": null,
  "status": false,
  "sector": "OPR"
}
```

### Rota de acompanhamento anterior

```http
GET https://api.rinaacc.com.br/accompaniment-previous/{id}
Authorization: {token}
```

Essa rota foi informada para itens anteriores. Nos testes feitos neste projeto
em 22 de maio de 2026, chamadas com `audit_id` e com IDs de item testados
retornaram HTTP 404.

Para leitura de detalhe dos itens anteriores, o comportamento observado foi:
usar o ID de `_accompanimentPrevious` em
`GET /accompanimentReport/{accompaniment_id}`. Validar novamente se a API mudar.

## Tratamento recomendado

Guardar uma linha por item de acompanhamento atual. O projeto atual salva um
envelope durante o fetch:

```json
{
  "audit_id": "audit-id",
  "period": "current",
  "item": {
    "_id": "accompaniment-id",
    "title": "Titulo",
    "description": "Descricao"
  }
}
```

Na transformacao, enriquecer cada item com campos do relatorio ou da auditoria:

| Campo | Origem |
| --- | --- |
| `audit_id` | relacao mantida no fetch |
| `item_id` | item `_id` |
| `date` | relatorio `date` ou auditoria `date` |
| `publication_date` | relatorio `publicationDate` ou auditoria `publicationDate` |
| `aircraft_prefix` | relatorio `aircraftPrefix` ou auditoria `aircraftPrefix` |
| `auditing_type` | relatorio `auditingType` ou auditoria `_auditing.auditorType` |
| `operator` | relatorio `operator` |
| `operator_abbreviation` | relatorio `operatorAbbreviation` |
| `base` | relatorio `base` |
| `base_abbreviation` | relatorio `baseAbbreviation` |
| `title` | item `title`; usar `Sem titulo` quando vazio |
| `description` | item `description`; usar string vazia quando ausente |
| `insert_date` | item `insertDate` |
| `solution_date` | item `solutionDate` |

Converter datas com tolerancia a valores invalidos e manter o `audit_id` para
filtrar acompanhamentos pelo mesmo recorte aplicado as auditorias.

## Normalizacao de titulos para ranking

Para rankings de frequencia, normalizar apenas variantes que representam o
mesmo titulo. Neste projeto:

| Variantes | Titulo normalizado |
| --- | --- |
| `Seguro RETA`, `SEGURO RETA` | `Seguro RETA` |
| `COCKPIT CAMERA`, `Cockpit Camera`, `Cockpit Câmera` | `Cockpit Camera` |
| `TAIL CAMERA`, `Tail Camera`, `Tail Câmera` | `Tail Camera` |

Remover ponto final e diferenca de caixa nesses titulos diretos antes de
agrupar. Frases com contexto adicional, como `Ausencia da Tail Camera` ou
`Vencimento do Seguro RETA`, devem continuar separadas ate haver uma regra de
negocio para junta-las.
