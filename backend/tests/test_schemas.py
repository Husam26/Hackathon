import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.schemas import Alert, IncidentCorpus, SentinelResponse


ROOT = Path(__file__).resolve().parents[2]


def test_incident_corpus_is_valid_and_demo_sequence_is_complete() -> None:
    payload = json.loads((ROOT / "data" / "incidents.json").read_text(encoding="utf-8"))

    corpus = IncidentCorpus.model_validate(payload)

    demo = sorted((item for item in corpus.incidents if item.seq <= 5), key=lambda item: item.seq)
    assert [item.seq for item in demo] == [1, 2, 3, 4, 5]
    assert [item.mttr_minutes for item in demo] == [90, 75, 40, 15, 3]
    assert sum(item.is_recurring_spine for item in demo) == 3


def test_alert_rejects_unknown_severity_and_fields() -> None:
    with pytest.raises(ValidationError):
        Alert.model_validate(
            {
                "service": "checkout-service",
                "fired_at": "2026-09-29T02:11:00Z",
                "severity": "CRITICAL",
                "metrics": {},
                "signals": [],
                "unexpected": True,
            }
        )


def test_sentinel_response_bounds_confidence() -> None:
    with pytest.raises(ValidationError):
        SentinelResponse.model_validate(
            {
                "classification": "NOVEL",
                "summary": "No matching history.",
                "confidence": 1.2,
            }
        )
