from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_manual_analysis_retains_and_replays_an_incident(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'manual-analysis.db').as_posix()}",
        groq_api_key=None,
        hindsight_api_key=None,
    )
    payload = {
        "title": "Checkout cache stampede resolved",
        "service": "checkout-service",
        "severity": "SEV-2",
        "occurred_at": "2026-09-29T10:15:00Z",
        "signals": ["p99 latency 3.2s", "cache hit ratio collapsed"],
        "root_cause": "Cache capacity was reduced during a configuration rollout",
        "mitigation": "Restored cache capacity and warmed hot checkout keys",
        "mttr_minutes": 12,
    }
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/incidents/manual/analyze", json=payload)
        assert created.status_code == 201
        run = created.json()
        assert run["source"] == "manual"
        assert run["incident"]["title"] == payload["title"]
        assert run["analysis"]["alert"]["service"] == payload["service"]
        incident_id = run["incident"]["id"]

        replayed = client.post(f"/api/incidents/{incident_id}/analyze")
        assert replayed.status_code == 200
        assert replayed.json()["source"] == "historical"
        assert replayed.json()["incident"]["id"] == incident_id

        artifacts = client.get(f"/api/incidents/{incident_id}/artifacts")
        assert artifacts.status_code == 200
        assert artifacts.json()[0]["label"] == "Open GitHub hotfix issue"
