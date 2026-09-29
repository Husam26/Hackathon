from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_azure_monitor_analysis_returns_a_standard_analysis_result(
    tmp_path: Path,
) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'azure.db').as_posix()}",
        groq_api_key=None,
        hindsight_api_key=None,
    )
    payload = {
        "data": {
            "essentials": {
                "alertRule": "checkout-service high latency",
                "severity": "Sev2",
                "firedDateTime": "2026-09-29T02:14:00Z",
                "alertTargetIDs": [
                    "/subscriptions/demo/resourceGroups/pay/providers/Microsoft.App/checkout-service"
                ],
            },
            "alertContext": {"condition": "p99 latency above 3000ms"},
        }
    }
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/integrations/azure-monitor", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["alert"]["service"] == "checkout-service"
    assert result["alert"]["severity"] == "SEV-2"
    assert "memory_impact" in result
