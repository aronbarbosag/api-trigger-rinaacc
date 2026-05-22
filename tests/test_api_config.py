from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import rina_trigger_api.api as api_module
import rina_trigger_api.config as config
from rina_trigger_api.api import app, get_service
from rina_trigger_api.config import Settings, load_settings
from rina_trigger_api.domain.trigger_items import TriggerItem
from rina_trigger_api.service import TriggerItemService


class FakeService:
    def __init__(self):
        self.calls = []

    def list_trigger_items(self, *, initial_date=None, final_date=None, terms=None):
        self.calls.append({"initial_date": initial_date, "final_date": final_date, "terms": terms})
        return [
            TriggerItem(
                audit_date=datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc),
                aircraft_prefix="PT-ABC",
                operator="Operator A",
                title="Trigger fuel check",
                description="Check fuel trigger limits",
                resolved=False,
            )
        ]


def test_api_returns_trigger_items_and_forwards_date_filters():
    fake_service = FakeService()
    app.dependency_overrides[get_service] = lambda: fake_service
    app.dependency_overrides[load_settings] = fake_settings
    client = TestClient(app)

    try:
        response = client.get(
            "/trigger-items",
            params={"initial_date": "2026-05-01", "final_date": "2026-05-15", "term": ["HISL", "vane"]},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == [
        {
            "audit_date": "10/05/2026",
            "aircraft_prefix": "PT-ABC",
            "operator": "Operator A",
            "title": "Trigger fuel check",
            "description": "Check fuel trigger limits",
            "resolved": False,
        }
    ]
    assert fake_service.calls == [{"initial_date": "2026-05-01", "final_date": "2026-05-15", "terms": ["HISL", "vane"]}]


def test_api_returns_422_for_invalid_date():
    class EmptyClient:
        def get_reports(self):
            return []

    app.dependency_overrides[get_service] = lambda: TriggerItemService(EmptyClient())
    app.dependency_overrides[load_settings] = fake_settings

    try:
        response = TestClient(app).get(
            "/trigger-items",
            params={"initial_date": "not-a-date"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid date value: not-a-date"}


def test_trigger_items_rate_limit_returns_retry_after():
    fake_service = FakeService()
    clear_app_state("request_limiter")
    app.dependency_overrides[get_service] = lambda: fake_service
    app.dependency_overrides[load_settings] = lambda: Settings(
        "user@example.com",
        "secret",
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
    )
    client = TestClient(app)

    try:
        first = client.get("/trigger-items")
        limited = client.get("/trigger-items")
    finally:
        app.dependency_overrides.clear()
        clear_app_state("request_limiter")

    assert first.status_code == 200
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
    assert limited.json() == {"detail": "Request limit exceeded."}


def test_api_reuses_and_closes_rina_client(monkeypatch):
    created_clients = []
    clear_app_state("rina_client")
    clear_app_state("request_limiter")

    class FakeRinaClient:
        def __init__(self, username, password, *, base_url):
            self.settings = (username, password, base_url)
            self.closed = False
            created_clients.append(self)

        def get_reports(self):
            return []

        def close(self):
            self.closed = True

    monkeypatch.setattr(api_module, "RinaAccClient", FakeRinaClient)
    app.dependency_overrides[load_settings] = lambda: Settings(
        "user@example.com",
        "secret",
        "https://example.test",
    )

    try:
        with TestClient(app) as client:
            assert client.get("/trigger-items").status_code == 200
            assert client.get("/trigger-items").status_code == 200
            assert len(created_clients) == 1
            assert created_clients[0].settings == (
                "user@example.com",
                "secret",
                "https://example.test",
            )
            assert not created_clients[0].closed
        assert created_clients[0].closed
    finally:
        app.dependency_overrides.clear()
        clear_app_state("rina_client")
        clear_app_state("request_limiter")


def test_health_returns_ok():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_typo_alias_returns_ok():
    response = TestClient(app).get("/heath")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_load_settings_reads_environment_and_reports_missing_values(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("USERNAME", "user@example.com")
    monkeypatch.setenv("PASSWORD", "secret")
    monkeypatch.setenv("RINA_BASE_URL", "https://example.test")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "12")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "15")

    assert load_settings() == Settings(
        "user@example.com",
        "secret",
        "https://example.test",
        12,
        15,
    )

    monkeypatch.delenv("USERNAME")
    monkeypatch.delenv("PASSWORD")
    with pytest.raises(RuntimeError, match="USERNAME, PASSWORD"):
        load_settings()


def test_load_settings_rejects_invalid_rate_limit(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("USERNAME", "user@example.com")
    monkeypatch.setenv("PASSWORD", "secret")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "0")

    with pytest.raises(RuntimeError, match="RATE_LIMIT_REQUESTS"):
        load_settings()


def clear_app_state(name):
    if hasattr(app.state, name):
        delattr(app.state, name)


def fake_settings():
    return Settings("user@example.com", "secret")
