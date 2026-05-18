from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, Query
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


app = FastAPI(title="RINA Trigger API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_service(settings: Settings = Depends(load_settings)) -> TriggerItemService:
    client = RinaAccClient(settings.username, settings.password, base_url=settings.base_url)
    return TriggerItemService(client)


@app.get("/trigger-items", response_model=list[TriggerItemResponse])
def list_trigger_items(
    initial_date: str | None = Query(None),
    final_date: str | None = Query(None),
    term: list[str] | None = Query(None),
    service: TriggerItemService = Depends(get_service),
) -> list[TriggerItemResponse]:
    return [
        TriggerItemResponse.model_validate(item)
        for item in service.list_trigger_items(initial_date=initial_date, final_date=final_date, terms=term)
    ]
