import httpx
import pytest

from backend.memory_client import HindsightMemoryClient
from backend.schemas import RecallQuery


@pytest.mark.asyncio
async def test_hindsight_recall_retries_transient_server_error() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"detail": "temporary provider error"})
        return httpx.Response(200, json={"results": []})

    client = HindsightMemoryClient(
        base_url="https://memory.example",
        bank_id="team/a",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await client.recall(
            RecallQuery(query="checkout incident", tags=["service:checkout-service"])
        )
    finally:
        await client.close()

    assert result == []
    assert calls == 2
