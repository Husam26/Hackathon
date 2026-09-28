from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_manual_incident_is_retained_and_listed(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'manual.db').as_posix()}",
        groq_api_key=None,
        hindsight_api_key=None,
    )
    payload = {
        "title": "Inventory cache timeout",
        "service": "inventory-service",
        "severity": "SEV-2",
        "occurred_at": "2026-09-29T10:15:00Z",
        "signals": ["cache timeouts", "p99 latency 2.4s"],
        "root_cause": "Cache connection pool exhaustion",
        "mitigation": "Restarted the cache client and raised the pool limit",
        "mttr_minutes": 18,
    }
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/incidents/manual", json=payload)
        assert response.status_code == 201
        incident = response.json()
        assert incident["id"].startswith("INC-")
        assert incident["root_cause"] == payload["root_cause"]
        assert incident["retained_memory_id"] == incident["id"]

        listed = client.get("/api/incidents")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [incident["id"]]
