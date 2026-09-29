import pytest

from backend.memory_client import LocalMemoryClient
from backend.resilience import FallbackMemoryProvider, ProviderUnavailableError
from backend.schemas import RecallQuery, RetainPayload
from backend.tests.test_memory_fallback import UnavailableMemory


@pytest.mark.asyncio
async def test_failed_remote_reset_is_not_reported_as_success() -> None:
    fallback = LocalMemoryClient()
    provider = FallbackMemoryProvider(UnavailableMemory(), fallback)
    await fallback.retain(
        RetainPayload(content="Transient local evidence", tags=["service:checkout"]),
        "INC-9002",
    )

    with pytest.raises(ProviderUnavailableError, match="could not be cleared"):
        await provider.clear()

    assert await fallback.recall(RecallQuery(query="evidence")) == []
