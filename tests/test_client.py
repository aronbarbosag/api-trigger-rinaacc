import httpx
import pytest

from rina_trigger_api.client import RinaAccClient, normalize_id


def test_client_logs_in_and_fetches_reports_from_result_envelope():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "token-123"})
        if request.url.path == "/reports":
            return httpx.Response(200, json={"result": [{"_id": "report-1"}, "ignored"]})
        raise AssertionError(f"unexpected request: {request.url.path}")

    client = RinaAccClient(
        "user@example.com",
        "secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.rinaacc.com.br"),
    )

    assert client.get_reports() == [{"_id": "report-1"}]
    assert seen[0].read() == b'{"login":"user@example.com","password":"secret"}'
    assert seen[1].headers["Authorization"] == "token-123"


def test_client_fetches_current_and_previous_accompaniment_objects_from_detail_route():
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "token-123"})
        if request.url.path == "/accompanimentReport/current-1":
            return httpx.Response(200, json={"docs": []})
        if request.url.path == "/accompanimentReport/previous-1":
            return httpx.Response(200, json={"docs": []})
        raise AssertionError(f"unexpected request: {request.url.path}")

    client = RinaAccClient(
        "user@example.com",
        "secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.rinaacc.com.br"),
    )

    assert client.get_current_accompaniment(" current-1 ") == {"docs": []}
    assert client.get_previous_accompaniment("previous-1") == {"docs": []}
    assert paths == ["/login", "/accompanimentReport/current-1", "/accompanimentReport/previous-1"]


def test_client_rejects_bad_response_shapes_and_empty_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "token-123"})
        if request.url.path == "/reports":
            return httpx.Response(200, json={"unexpected": True})
        if request.url.path == "/accompanimentReport/current-1":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected request: {request.url.path}")

    client = RinaAccClient(
        "user@example.com",
        "secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.rinaacc.com.br"),
    )

    with pytest.raises(ValueError, match="Reports response"):
        client.get_reports()
    with pytest.raises(ValueError, match="Accompaniment id cannot be empty"):
        normalize_id(" ")
    with pytest.raises(ValueError, match="did not return an object"):
        client.get_current_accompaniment("current-1")


def test_client_rejects_login_without_token_and_accepts_single_report():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={})
        raise AssertionError(f"unexpected request: {request.url.path}")

    client = RinaAccClient(
        "user@example.com",
        "secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.rinaacc.com.br"),
    )

    with pytest.raises(ValueError, match="token"):
        client.login()

    def single_report_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "token-123"})
        if request.url.path == "/reports":
            return httpx.Response(200, json={"_id": "report-1"})
        raise AssertionError(f"unexpected request: {request.url.path}")

    client = RinaAccClient(
        "user@example.com",
        "secret",
        http_client=httpx.Client(
            transport=httpx.MockTransport(single_report_handler),
            base_url="https://api.rinaacc.com.br",
        ),
    )

    assert client.get_reports() == [{"_id": "report-1"}]
