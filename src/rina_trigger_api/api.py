from __future__ import annotations

from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from threading import Lock
from time import monotonic
from typing import Deque

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, field_serializer

from .client import RinaAccClient
from .config import Settings, load_settings
from .service import TriggerItemService


class TriggerItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_date: datetime | None
    aircraft_prefix: str | None
    operator: str | None
    title: str | None
    description: str | None
    resolved: bool | None

    @field_serializer("audit_date")
    def serialize_audit_date(self, value: datetime | None) -> str | None:
        return value.strftime("%d/%m/%Y") if value else None


class RequestLimiter:
    def __init__(self, requests: int, window_seconds: int) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self._lock = Lock()
        self._timestamps: Deque[float] = deque()

    def check(self, now: float | None = None) -> int | None:
        current = monotonic() if now is None else now
        threshold = current - self.window_seconds
        with self._lock:
            while self._timestamps and self._timestamps[0] <= threshold:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.requests:
                retry_after = self.window_seconds - (current - self._timestamps[0])
                return max(1, int(retry_after + 0.999))
            self._timestamps.append(current)
        return None


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield
    rina_client = getattr(application.state, "rina_client", None)
    if rina_client is not None:
        rina_client.close()
        del application.state.rina_client


app = FastAPI(title="RINA Trigger API", lifespan=lifespan)
client_lock = Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/heath", include_in_schema=False)
def heath_typo_alias() -> dict[str, str]:
    return health()


def get_service(request: Request, settings: Settings = Depends(load_settings)) -> TriggerItemService:
    client = getattr(request.app.state, "rina_client", None)
    if client is None:
        with client_lock:
            client = getattr(request.app.state, "rina_client", None)
            if client is None:
                client = RinaAccClient(settings.username, settings.password, base_url=settings.base_url)
                request.app.state.rina_client = client
    return TriggerItemService(client)


def enforce_request_limit(
    request: Request,
    settings: Settings = Depends(load_settings),
) -> None:
    limiter = getattr(request.app.state, "request_limiter", None)
    limiter_config = (settings.rate_limit_requests, settings.rate_limit_window_seconds)
    if limiter is None or (limiter.requests, limiter.window_seconds) != limiter_config:
        limiter = RequestLimiter(*limiter_config)
        request.app.state.request_limiter = limiter
    retry_after = limiter.check()
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Request limit exceeded.",
            headers={"Retry-After": str(retry_after)},
        )


@app.get("/trigger-items", response_model=list[TriggerItemResponse])
def list_trigger_items(
    initial_date: str | None = Query(None),
    final_date: str | None = Query(None),
    term: list[str] | None = Query(None),
    _: None = Depends(enforce_request_limit),
    service: TriggerItemService = Depends(get_service),
) -> list[TriggerItemResponse]:
    try:
        items = service.list_trigger_items(initial_date=initial_date, final_date=final_date, terms=term)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [
        TriggerItemResponse.model_validate(item)
        for item in items
    ]
