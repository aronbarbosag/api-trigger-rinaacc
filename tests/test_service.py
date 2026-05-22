import httpx
import pytest

from rina_trigger_api.service import TriggerItemService, coerce_end, coerce_start, date_in_range


class FakeRinaClient:
    def __init__(self):
        self.current_calls = []
        self.previous_calls = []

    def get_reports(self):
        return [
            {
                "_id": "before",
                "_auditing": {"date": "2026-04-30T23:59:59Z"},
                "aircraftprefix": "PT-OLD",
                "operator": "Old Operator",
                "_accompaniment": ["ignored"],
            },
            {
                "_id": "report-1",
                "_auditing": {"date": "2026-05-10T10:00:00Z"},
                "aircraftprefix": "PT-ABC",
                "operator": "Operator A",
                "_accompaniment": ["current-1", "current-2"],
                "_accompanimentPrevious": ["previous-1"],
            },
            {
                "_id": "report-empty",
                "_auditing": {"date": "2026-05-11T10:00:00Z"},
                "_accompaniment": [],
                "_accompanimentPrevious": None,
            },
            {
                "_id": "after",
                "_auditing": {"date": "2026-05-16T00:00:00Z"},
                "aircraftprefix": "PT-NEW",
                "_accompaniment": ["ignored-after"],
            },
        ]

    def get_current_accompaniment(self, accompaniment_id):
        self.current_calls.append(accompaniment_id)
        return {
            "current-1": {
                "_id": "current-1",
                "title": "Trigger fuel check",
                "description": "Normal",
                "status": True,
            },
            "current-2": {
                "_id": "current-2",
                "title": "HISL check",
                "description": "Sem ocorrencia",
                "status": False,
            },
        }[accompaniment_id]

    def get_previous_accompaniment(self, accompaniment_id):
        self.previous_calls.append(accompaniment_id)
        return {
            "_id": "previous-1",
            "title": "Historico",
            "description": "Gatilho anterior",
            "solutionDate": "2026-05-10T10:00:00Z",
        }


def test_service_returns_only_items_with_trigger_terms_and_required_fields():
    client = FakeRinaClient()
    service = TriggerItemService(client)

    items = service.list_trigger_items(initial_date="2026-05-01", final_date="2026-05-15")

    assert client.current_calls == ["current-1", "current-2"]
    assert client.previous_calls == ["previous-1"]
    assert [item.title for item in items] == ["Trigger fuel check", "Historico"]
    assert [item.description for item in items] == ["Normal", "Gatilho anterior"]
    assert [item.resolved for item in items] == [True, True]
    assert [item.aircraft_prefix for item in items] == ["PT-ABC", "PT-ABC"]
    assert [item.operator for item in items] == ["Operator A", "Operator A"]
    assert items[0].audit_date.isoformat() == "2026-05-10T10:00:00+00:00"


def test_service_can_filter_with_custom_terms():
    client = FakeRinaClient()
    service = TriggerItemService(client)

    items = service.list_trigger_items(
        initial_date="2026-05-01",
        final_date="2026-05-15",
        terms=["hisl"],
    )

    assert [item.title for item in items] == ["HISL check"]


class PreviousServerErrorClient(FakeRinaClient):
    def get_reports(self):
        return [
            {
                "_id": "report-1",
                "_auditing": {"date": "2026-05-10T10:00:00Z"},
                "_accompaniment": ["current-1"],
                "_accompanimentPrevious": ["previous-1"],
            }
        ]

    def get_previous_accompaniment(self, accompaniment_id):
        self.previous_calls.append(accompaniment_id)
        request = httpx.Request("GET", f"https://api.rinaacc.com.br/accompanimentReport/{accompaniment_id}")
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError("server error", request=request, response=response)


def test_service_ignores_previous_endpoint_500_and_keeps_current_items():
    client = PreviousServerErrorClient()
    service = TriggerItemService(client)

    items = service.list_trigger_items(initial_date="2026-05-01", final_date="2026-05-15")

    assert client.current_calls == ["current-1"]
    assert client.previous_calls == ["previous-1"]
    assert [item.title for item in items] == ["Trigger fuel check"]


class BadGatewayClient(PreviousServerErrorClient):
    def get_current_accompaniment(self, accompaniment_id):
        request = httpx.Request("GET", f"https://api.rinaacc.com.br/accompanimentReport/{accompaniment_id}")
        response = httpx.Response(502, request=request)
        raise httpx.HTTPStatusError("bad gateway", request=request, response=response)


def test_service_reraises_non_500_detail_errors():
    with pytest.raises(httpx.HTTPStatusError):
        TriggerItemService(BadGatewayClient()).list_trigger_items(initial_date="2026-05-01")


def test_date_helpers_handle_open_ranges_invalid_values_and_date_boundaries():
    assert coerce_start("2026-05-01").isoformat() == "2026-05-01T00:00:00+00:00"
    assert coerce_end("2026-05-01").isoformat() == "2026-05-01T23:59:59.999999+00:00"
    assert date_in_range(None, None, None)
    assert not date_in_range(None, coerce_start("2026-05-01"), None)
    with pytest.raises(ValueError, match="Invalid date value"):
        coerce_start("invalid")
