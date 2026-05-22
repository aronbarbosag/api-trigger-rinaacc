import httpx
from fastapi.testclient import TestClient

from rina_trigger_api.api import app, get_service
from rina_trigger_api.client import RinaAccClient
from rina_trigger_api.config import Settings, load_settings
from rina_trigger_api.service import TriggerItemService


def build_service_with_mock_transport(handler):
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.rinaacc.com.br"
    )
    client = RinaAccClient("user@example.com", "secret", http_client=http_client)
    return TriggerItemService(client)


def test_integration_returns_trigger_items_from_api():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "token-123"})
        if request.url.path == "/reports":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "_id": "report-1",
                            "date": "2026-05-10T10:00:00.000Z",
                            "_auditing": {"date": "2026-05-10T10:00:00.000Z"},
                            "aircraftPrefix": "PT-ABC",
                            "operator": "Operator A",
                            "operatorAbbreviation": "OPA",
                            "_accompaniment": ["current-1"],
                            "_accompanimentPrevious": ["previous-1"],
                        }
                    ]
                },
            )
        if request.url.path == "/accompanimentReport/current-1":
            return httpx.Response(
                200,
                json={
                    "_id": "current-1",
                    "title": "Trigger fuel check",
                    "description": "Normal",
                },
            )
        if request.url.path == "/accompanimentReport/previous-1":
            return httpx.Response(
                200,
                json={
                    "_id": "previous-1",
                    "title": "Historico",
                    "description": "HISL anterior",
                    "status": False,
                },
            )
        raise AssertionError(f"unexpected request: {request.url.path}")

    app.dependency_overrides[get_service] = lambda: build_service_with_mock_transport(
        handler
    )
    app.dependency_overrides[load_settings] = lambda: Settings("user@example.com", "secret")
    client = TestClient(app)

    try:
        response = client.get(
            "/trigger-items",
            params={"initial_date": "2026-05-01", "final_date": "2026-05-15", "term": "HISL"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload == [
        {
            "audit_date": "10/05/2026",
            "aircraft_prefix": "PT-ABC",
            "operator": "Operator A",
            "title": "Historico",
            "description": "HISL anterior",
            "resolved": False,
        },
    ]


def test_integration_default_terms_include_gatilhos():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "token-123"})
        if request.url.path == "/reports":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "_id": "report-1",
                            "date": "2026-05-10T10:00:00.000Z",
                            "_auditing": {"date": "2026-05-10T10:00:00.000Z"},
                            "aircraftPrefix": "PT-ABC",
                            "operator": "Operator A",
                            "_accompaniment": ["current-1"],
                            "_accompanimentPrevious": ["previous-1"],
                        }
                    ]
                },
            )
        if request.url.path == "/accompanimentReport/current-1":
            return httpx.Response(
                200,
                json={
                    "_id": "current-1",
                    "title": "Door check",
                    "description": "Sem ocorrencia",
                },
            )
        if request.url.path == "/accompanimentReport/previous-1":
            return httpx.Response(
                200,
                json={
                    "_id": "previous-1",
                    "title": "Gatilhos anteriores",
                    "description": "Sem ocorrencia",
                },
            )
        raise AssertionError(f"unexpected request: {request.url.path}")

    app.dependency_overrides[get_service] = lambda: build_service_with_mock_transport(
        handler
    )
    app.dependency_overrides[load_settings] = lambda: Settings("user@example.com", "secret")
    client = TestClient(app)

    try:
        response = client.get(
            "/trigger-items",
            params={"initial_date": "2026-05-01", "final_date": "2026-05-15"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "audit_date": "10/05/2026",
            "aircraft_prefix": "PT-ABC",
            "operator": "Operator A",
            "title": "Gatilhos anteriores",
            "description": "Sem ocorrencia",
            "resolved": None,
        },
    ]
