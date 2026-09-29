from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_analysis_reports_memory_impact_and_preference_bias(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'impact.db').as_posix()}",
        groq_api_key=None,
        hindsight_api_key=None,
    )
    alert = {
        "service": "checkout-service",
        "fired_at": "2026-09-29T02:14:00Z",
        "severity": "SEV-2",
        "metrics": {},
        "signals": ["p99 latency 3.2s", "5xx rate 12%"],
        "recent_deploys": [],
    }
    with TestClient(create_app(settings)) as client:
        result = client.post(
            "/api/analyze/with-preferences",
            json={
                "alert": alert,
                "memory_preferences": {
                    "recency": "past_30_days",
                    "severities": ["SEV-1", "SEV-2"],
                },
            },
        )

    assert result.status_code == 200
    impact = result.json()["memory_impact"]
    assert impact["recalled_count"] == 0
    assert impact["grounded_citation_count"] == 0
    assert impact["temporal_bias_applied"] is True
    assert impact["severity_tags_applied"] == ["severity:sev-1", "severity:sev-2"]
