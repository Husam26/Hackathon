from datetime import datetime, timezone

import httpx
import pytest

from backend.memory_client import LocalMemoryClient
from backend.resilience import FallbackMemoryProvider
from backend.schemas import RecallQuery, RetainPayload


class UnavailableMemory:
    name = "hindsight"

    async def retain(self, payload: RetainPayload, document_id: str) -> str:
        raise httpx.ConnectError("memory provider unavailable")

    async def recall(self, query: RecallQuery):
        raise httpx.ConnectError("memory provider unavailable")

    async def get_mental_model(self, model_id: str):
        raise httpx.ConnectError("memory provider unavailable")

    async def ensure_mental_model(
        self, model_id: str, name: str, source_query: str, tags: list[str]
    ) -> None:
        raise httpx.ConnectError("memory provider unavailable")

    async def clear(self) -> None:
        raise httpx.ConnectError("memory provider unavailable")

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_memory_fallback_preserves_current_process_evidence() -> None:
    provider = FallbackMemoryProvider(UnavailableMemory(), LocalMemoryClient())
    payload = RetainPayload(
        content="Checkout latency mitigated by restoring cache capacity.",
        timestamp=datetime(2026, 9, 29, tzinfo=timezone.utc),
        tags=["service:checkout-service", "severity:sev-2"],
    )

    assert await provider.retain(payload, "INC-9001") == "INC-9001"
    recalled = await provider.recall(
        RecallQuery(
            query="checkout-service latency",
            tags=["service:checkout-service"],
        )
    )

    assert provider.name == "hindsight -> local fallback"
    assert [memory.id for memory in recalled] == ["INC-9001"]
