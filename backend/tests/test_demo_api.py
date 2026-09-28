from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_demo_replays_learning_curve(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
        groq_api_key=None,
        hindsight_api_key=None,
        hindsight_base_url="https://api.hindsight.vectorize.io",
    )
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["providers"] == {
            "memory": "local",
            "analysis": "grounded-rules",
        }

        results = [client.post("/api/demo/step") for _ in range(5)]
        assert all(response.status_code == 200 for response in results)
        payloads = [response.json() for response in results]

        assert payloads[0]["analysis"]["response"]["classification"] == "NOVEL"
        assert payloads[2]["analysis"]["response"]["classification"] == "NOVEL"
        assert payloads[3]["analysis"]["response"]["occurrence_count"] == 2
        final = payloads[4]["analysis"]
        assert final["response"]["classification"] == "KNOWN_PATTERN"
        assert final["response"]["occurrence_count"] == 3
        assert final["response"]["mttr_trend_minutes"] == [90, 15, 3]
        assert final["mental_model"] is not None
        assert set(final["response"]["cited_memory_ids"]) == {"INC-1047", "INC-1074"}

        assert client.post("/api/demo/step").status_code == 409
        assert len(client.get("/api/incidents").json()) == 5
        assert client.post("/api/demo/reset").status_code == 204
        assert client.get("/api/incidents").json() == []
