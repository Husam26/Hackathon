import json

import httpx
import pytest

from backend.memory_client import HindsightMemoryClient
from backend.schemas import RecallQuery, RetainPayload


@pytest.mark.asyncio
async def test_hindsight_retain_uses_stable_document_id() -> None:
    seen: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.raw_path.decode()
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"operation_id": "op-123"})

    client = HindsightMemoryClient(
        base_url="https://memory.example",
        bank_id="team/a",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await client.retain(
            RetainPayload(
                content="Resolved incident", tags=["service:checkout-service"]
            ),
            "INC-1",
        )
    finally:
        await client.close()

    assert result == "op-123"
    assert seen["path"] == "/v1/default/banks/team%2Fa/memories"
    assert seen["body"]["items"][0]["document_id"] == "INC-1"
    assert seen["body"]["items"][0]["tags"] == ["service:checkout-service"]


@pytest.mark.asyncio
async def test_hindsight_recall_maps_current_response_shape() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["types"] == ["experience", "world"]
        assert body["tags_match"] == "all_strict"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "fact-1",
                        "document_id": "INC-1047",
                        "text": "Redis pool exhausted.",
                        "type": "experience",
                        "tags": ["service:checkout-service"],
                        "scores": {"final": 0.91},
                        "occurred_start": "2026-09-10T02:14:00Z",
                    }
                ]
            },
        )

    client = HindsightMemoryClient(
        base_url="https://memory.example",
        bank_id="acme-sre",
        api_key=None,
        transport=httpx.MockTransport(handler),
    )
    try:
        memories = await client.recall(
            RecallQuery(
                query="checkout latency",
                tags=["service:checkout-service"],
                fact_types=["experience", "world"],
            )
        )
    finally:
        await client.close()

    assert memories[0].id == "INC-1047"
    assert memories[0].recall_score == 0.91
