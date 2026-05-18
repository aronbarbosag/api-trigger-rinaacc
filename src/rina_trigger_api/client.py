from __future__ import annotations

from typing import Any

import httpx


class RinaAccClient:
    def __init__(
        self,
        username: str,
        password: str,
        *,
        base_url: str = "https://api.rinaacc.com.br",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self._client = http_client or httpx.Client(base_url=base_url, timeout=30)
        self._token: str | None = None

    def login(self) -> str:
        response = self._client.post(
            "/login",
            json={"login": self.username, "password": self.password},
        )
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            raise ValueError("Login response did not include a token.")
        self._token = str(token)
        return self._token

    def get_reports(self) -> list[dict[str, Any]]:
        payload = self._get_json("/reports")
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("result", "results", "reports", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            if "_id" in payload:
                return [payload]
        raise ValueError("Reports response is not a supported format.")

    def get_current_accompaniment(self, report_id: str) -> dict[str, Any]:
        return self._get_object(f"/accompanimentReport/{normalize_id(report_id)}")

    def get_previous_accompaniment(self, report_id: str) -> dict[str, Any]:
        return self._get_object(f"/accompaniments-previous/{normalize_id(report_id)}")

    def _get_object(self, path: str) -> dict[str, Any]:
        payload = self._get_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"Endpoint {path} did not return an object.")
        return payload

    def _get_json(self, path: str) -> Any:
        response = self._client.get(path, headers={"Authorization": self._token or self.login()})
        response.raise_for_status()
        return response.json()


def normalize_id(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("Report id cannot be empty.")
    return normalized

