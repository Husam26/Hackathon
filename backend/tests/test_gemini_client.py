import json

import httpx
import pytest

from backend.gemini_client import FallbackAnalyzer, GeminiAnalyzer
from backend.schemas import Alert, RecalledMemory, SentinelResponse


def alert() -> Alert:
    return Alert.model_validate(
        {
            "service": "checkout-service",
            "fired_at": "2026-09-29T02:11:00Z",
            "severity": "SEV-2",
            "metrics": {},
            "signals": ["p99 latency 3.3s"],
        }
    )


@pytest.mark.asyncio
async def test_gemini_uses_json_mode_and_validates_citations() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/v1beta/models/gemini-test:generateContent"
        assert request.headers["x-goog-api-key"] == "test-key"
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "classification": "KNOWN_PATTERN",
                                            "summary": "Retrieved evidence matches.",
                                            "hypotheses": [],
                                            "recommended_mitigation": None,
                                            "occurrence_count": 1,
                                            "confidence": 0.8,
                                            "cited_memory_ids": ["INC-1047"],
                                            "mttr_trend_minutes": [],
                                            "escalation": None,
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    client = GeminiAnalyzer(
        api_key="test-key",
        model="gemini-test",
        base_url="https://gemini.example/v1beta",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await client.analyze(
            alert(),
            [
                RecalledMemory(
                    id="INC-1047",
                    content="Resolved incident",
                    tags=[],
                    recall_score=0.9,
                )
            ],
            None,
        )
    finally:
        await client.close()

    assert result.cited_memory_ids == ["INC-1047"]


@pytest.mark.asyncio
async def test_fallback_uses_secondary_after_primary_provider_error() -> None:
    class FailingAnalyzer:
        name = "primary"

        async def analyze(self, *_args: object) -> SentinelResponse:
            raise httpx.ConnectError("unavailable")

        async def close(self) -> None:
            return None

    class WorkingAnalyzer:
        name = "secondary"

        async def analyze(self, *_args: object) -> SentinelResponse:
            return SentinelResponse(
                classification="NOVEL",
                summary="Backup response.",
                confidence=0.5,
            )

        async def close(self) -> None:
            return None

    result = await FallbackAnalyzer(FailingAnalyzer(), WorkingAnalyzer()).analyze(
        alert(), [], None
    )

    assert result.summary == "Backup response."
