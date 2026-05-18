from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import rina_trigger_api.config as config
from rina_trigger_api.api import app, get_service
from rina_trigger_api.config import Settings, load_settings
from rina_trigger_api.domain.trigger_items import TriggerItem


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
    client = TestClient(app)

    response = client.get(
        "/trigger-items",
        params={"initial_date": "2026-05-01", "final_date": "2026-05-15", "term": ["HISL", "vane"]},
    )

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


def test_health_returns_ok():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_load_settings_reads_environment_and_reports_missing_values(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("USERNAME", "user@example.com")
    monkeypatch.setenv("PASSWORD", "secret")
    monkeypatch.setenv("RINA_BASE_URL", "https://example.test")

    assert load_settings() == Settings("user@example.com", "secret", "https://example.test")

    monkeypatch.delenv("USERNAME")
    monkeypatch.delenv("PASSWORD")
    with pytest.raises(RuntimeError, match="USERNAME, PASSWORD"):
        load_settings()
