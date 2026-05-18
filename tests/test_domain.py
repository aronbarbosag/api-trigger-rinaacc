from datetime import datetime

from rina_trigger_api.domain.trigger_items import (
    accompaniment_ids,
    accompaniment_resolved,
    aircraft_prefix,
    build_trigger_item,
    extract_accompaniment_items,
    item_matches_terms,
    item_matches_trigger_terms,
    operator_name,
    parse_datetime,
    report_audit_date,
    report_id,
)


def test_item_matches_trigger_terms_in_title_or_description_with_normalization():
    assert item_matches_trigger_terms({"title": " Engine TRIGGER inspection "})
    assert item_matches_trigger_terms({"description": "Acionar gatilho de revisao"})
    assert item_matches_trigger_terms({"title": "Gatínho operacional"})
    assert not item_matches_trigger_terms({"title": "Inspecao comum", "description": "Sem termo alvo"})


def test_item_matches_custom_terms_in_title_or_description():
    assert item_matches_terms({"title": "HISL - High Intensity Strobe Light"}, ["hisl"])
    assert item_matches_terms({"description": "Replace VÁNE actuator"}, ["vane"])
    assert not item_matches_terms({"title": "Door check"}, ["hisl", "vane"])


def test_build_trigger_item_extracts_required_public_fields_from_known_report_shapes():
    report = {
        "_id": "report-1",
        "_auditing": {"date": "2026-05-10T10:00:00Z"},
        "_aircraft": {"prefix": "PT-ABC"},
        "_operator": {"name": "RINA Operator"},
    }

    item = build_trigger_item(
        report,
        {
            "name": "Trigger alternativo",
            "description": "Descricao do acompanhamento",
            "status": True,
        },
    )

    assert item.audit_date == datetime.fromisoformat("2026-05-10T10:00:00+00:00")
    assert item.aircraft_prefix == "PT-ABC"
    assert item.operator == "RINA Operator"
    assert item.title == "Trigger alternativo"
    assert item.description == "Descricao do acompanhamento"
    assert item.resolved is True


def test_accompaniment_resolved_accepts_boolean_status_and_solution_date_fallback():
    assert accompaniment_resolved({"status": False}) is False
    assert accompaniment_resolved({"isResolved": "yes"}) is True
    assert accompaniment_resolved({"solutionDate": "2026-05-10T10:00:00Z"}) is True
    assert accompaniment_resolved({"status": "unknown"}) is None
    assert accompaniment_resolved({}) is None


def test_report_helpers_accept_fallback_fields_and_invalid_dates():
    report = {
        "_id": " report-2 ",
        "publicationDate": "not-a-date",
        "aircraftPrefix": "PR-XYZ",
        "operatorAbbreviation": "OPR",
        "_accompaniment": ["a", "", None, " b "],
    }

    assert report_id(report) == "report-2"
    assert report_audit_date(report) is None
    assert aircraft_prefix(report) == "PR-XYZ"
    assert operator_name(report) == "OPR"
    assert accompaniment_ids(report, "_accompaniment") == ["a", "b"]


def test_extract_accompaniment_items_accepts_supported_response_envelopes():
    assert extract_accompaniment_items([{"_id": "1"}, "ignored"]) == [{"_id": "1"}]
    assert extract_accompaniment_items({"docs": [{"_id": "2"}]}) == [{"_id": "2"}]
    assert extract_accompaniment_items({"result": {"_id": "3"}}) == [{"_id": "3"}]
    assert extract_accompaniment_items({"_id": "4"}) == [{"_id": "4"}]
    assert extract_accompaniment_items("unsupported") == []


def test_parse_datetime_accepts_none_datetime_and_iso_z():
    existing = datetime(2026, 5, 10)

    assert parse_datetime(None) is None
    assert parse_datetime(existing) is existing
    assert parse_datetime("2026-05-10T10:00:00Z").isoformat() == "2026-05-10T10:00:00+00:00"
