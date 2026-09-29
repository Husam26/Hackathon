from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_architecture_workflow_exposes_current_mermaid_diagrams(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'workflow.db').as_posix()}",
        groq_api_key=None,
        hindsight_api_key=None,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/architecture/workflow")

    assert response.status_code == 200
    body = response.json()
    assert body["sequence_diagram"].startswith("sequenceDiagram")
    assert "Azure Monitor" in body["sequence_diagram"]
    assert body["architecture_flowchart"].startswith("flowchart TD")
    assert "backend/http/routes" in body["architecture_flowchart"]
