from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from rina_trigger_api.api import app


def test_e2e_real_trigger_items_endpoint_returns_output():
    load_dotenv()
    if not os.getenv("USERNAME") or not os.getenv("PASSWORD"):
        pytest.skip("Real E2E requires USERNAME and PASSWORD in the environment or .env file.")

    initial_date = os.getenv("E2E_INITIAL_DATE", "2026-05-01")
    final_date = os.getenv("E2E_FINAL_DATE", "2026-05-18")
    term = os.getenv("E2E_SEARCH_TERM", "HISL")

    response = TestClient(app).get(
        "/trigger-items",
        params={"initial_date": initial_date, "final_date": final_date, "term": term},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload, f"Expected real RINA data for {term!r} between {initial_date} and {final_date}."

    for item in payload:
        assert item["audit_date"]
        assert item["aircraft_prefix"]
        assert item["operator"]
        assert item["title"]
