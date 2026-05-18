from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any

DEFAULT_SEARCH_TERMS = (
    "trigger",
    "Trigger",
    "TRIGGER",
    "gatilho",
    "Gatilho",
    "GATILHO",
)


@dataclass(frozen=True)
class TriggerItem:
    audit_date: datetime | None
    aircraft_prefix: str | None
    operator: str | None
    title: str | None
    description: str | None
    resolved: bool | None


def item_matches_trigger_terms(item: dict[str, Any]) -> bool:
    return item_matches_terms(item, DEFAULT_SEARCH_TERMS)


def item_matches_terms(
    item: dict[str, Any], terms: list[str] | tuple[str, ...]
) -> bool:
    normalized_terms = normalize_terms(terms)
    if not normalized_terms:
        return False
    title = normalize_search_text(item.get("title") or item.get("name"))
    description = normalize_search_text(item.get("description"))
    searchable = f"{title} {description}"
    return any(term in searchable for term in normalized_terms)


def normalize_terms(terms: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not terms:
        return DEFAULT_SEARCH_TERMS
    normalized = tuple(
        normalized_term
        for term in terms
        if (normalized_term := normalize_search_text(term))
    )
    return normalized or DEFAULT_SEARCH_TERMS


def build_trigger_item(
    report: dict[str, Any], accompaniment: dict[str, Any]
) -> TriggerItem:
    return TriggerItem(
        audit_date=report_audit_date(report),
        aircraft_prefix=aircraft_prefix(report),
        operator=operator_name(report),
        title=string_or_none(accompaniment.get("title") or accompaniment.get("name")),
        description=string_or_none(accompaniment.get("description")),
        resolved=accompaniment_resolved(accompaniment),
    )


def accompaniment_resolved(accompaniment: dict[str, Any]) -> bool | None:
    for key in ("resolved", "isResolved", "done", "closed", "completed", "status"):
        if key in accompaniment:
            return bool_or_none(accompaniment.get(key))
    if string_or_none(
        accompaniment.get("solutionDate") or accompaniment.get("resolvedAt")
    ):
        return True
    return None


def normalize_search_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    without_accents = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip().casefold()


def report_audit_date(report: dict[str, Any]) -> datetime | None:
    auditing = report.get("_auditing")
    auditing_date = auditing.get("date") if isinstance(auditing, dict) else None
    value = report.get("date") or auditing_date or report.get("publicationDate")
    return parse_datetime(value)


def report_id(report: dict[str, Any]) -> str:
    return str(report.get("_id") or "").strip()


def accompaniment_ids(report: dict[str, Any], key: str) -> list[str]:
    raw_value = report.get(key)
    values = raw_value if isinstance(raw_value, (list, tuple, set)) else [raw_value]
    return [
        str(value).strip()
        for value in values
        if value is not None and str(value).strip()
    ]


def extract_accompaniment_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("docs", "result", "results", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
    return [payload] if "_id" in payload else []


def aircraft_prefix(report: dict[str, Any]) -> str | None:
    aircraft = report.get("_aircraft")
    nested = aircraft.get("prefix") if isinstance(aircraft, dict) else None
    prefix = (
        report.get("aircraftPrefix")
        or report.get("aircraftprefix")
        or report.get("aircraft_prefix")
        or nested
    )
    return string_or_none(prefix)


def operator_name(report: dict[str, Any]) -> str | None:
    operator_payload = report.get("_operator")
    nested = None
    if isinstance(operator_payload, dict):
        nested = (
            operator_payload.get("name")
            or operator_payload.get("abbreviation")
            or operator_payload.get("title")
        )
    operator = report.get("operator") or report.get("operatorAbbreviation") or nested

    return string_or_none(operator)


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    text = normalize_search_text(value)
    if text in {
        "true",
        "resolved",
        "done",
        "closed",
        "completed",
        "complete",
        "concluido",
        "sim",
        "yes",
        "1",
    }:
        return True
    if text in {
        "false",
        "open",
        "pending",
        "unresolved",
        "nao resolvido",
        "nao",
        "no",
        "0",
    }:
        return False
    return None
