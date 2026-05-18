from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Protocol

import httpx

from .domain.trigger_items import (
    TriggerItem,
    accompaniment_ids,
    build_trigger_item,
    extract_accompaniment_items,
    item_matches_terms,
    normalize_terms,
    parse_datetime,
    report_audit_date,
    report_id,
)


class RinaClientProtocol(Protocol):
    def get_reports(self) -> list[dict[str, Any]]: ...

    def get_current_accompaniment(self, report_id: str) -> dict[str, Any]: ...

    def get_previous_accompaniment(self, report_id: str) -> dict[str, Any]: ...


class TriggerItemService:
    def __init__(self, client: RinaClientProtocol) -> None:
        self.client = client

    def list_trigger_items(
        self,
        *,
        initial_date: str | date | datetime | None = None,
        final_date: str | date | datetime | None = None,
        terms: list[str] | tuple[str, ...] | None = None,
    ) -> list[TriggerItem]:
        start = coerce_start(initial_date) if initial_date is not None else None
        end = coerce_end(final_date) if final_date is not None else None
        normalized_terms = normalize_terms(terms)
        rows: list[TriggerItem] = []

        for report in self.client.get_reports():
            audit_date = report_audit_date(report)
            if not date_in_range(audit_date, start, end):
                continue

            current_items = self._items_for(report, "_accompaniment", "current")
            previous_items = self._items_for(report, "_accompanimentPrevious", "previous")
            for item in current_items + previous_items:
                if item_matches_terms(item, normalized_terms):
                    rows.append(build_trigger_item(report, item))

        return rows

    def _items_for(self, report: dict[str, Any], ids_key: str, source: str) -> list[dict[str, Any]]:
        rid = report_id(report)
        if not rid or not accompaniment_ids(report, ids_key):
            return []
        try:
            payload = (
                self.client.get_current_accompaniment(rid)
                if source == "current"
                else self.client.get_previous_accompaniment(rid)
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 500:
                return []
            raise
        return extract_accompaniment_items(payload)


def date_in_range(
    value: datetime | None,
    start: datetime | None,
    end: datetime | None,
) -> bool:
    if value is None:
        return start is None and end is None
    normalized = ensure_aware_utc(value)
    return (start is None or normalized >= start) and (end is None or normalized <= end)


def coerce_start(value: str | date | datetime) -> datetime:
    parsed = parse_datetime_or_raise(value)
    if isinstance(value, datetime):
        return ensure_aware_utc(parsed)
    return datetime.combine(parsed.date(), time.min, tzinfo=timezone.utc)


def coerce_end(value: str | date | datetime) -> datetime:
    parsed = parse_datetime_or_raise(value)
    if isinstance(value, datetime) or (isinstance(value, str) and "T" in value):
        return ensure_aware_utc(parsed)
    return datetime.combine(parsed.date(), time.max, tzinfo=timezone.utc)


def parse_datetime_or_raise(value: str | date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid date value: {value}")
    return parsed


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
