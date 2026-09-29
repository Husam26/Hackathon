"""Resilience decorators for provider-facing ports.

The application keeps Hindsight as the preferred memory system, while a local
in-process mirror prevents an unavailable remote provider from turning an
operator-facing incident analysis into a 500 response.
"""

from __future__ import annotations

import logging

import httpx

from backend.memory_client import MemoryProvider
from backend.schemas import MentalModel, RecallQuery, RecalledMemory, RetainPayload


logger = logging.getLogger(__name__)


class ProviderUnavailableError(RuntimeError):
    """Raised when a requested remote-only operation cannot be completed."""


class FallbackMemoryProvider:
    """Use a local mirror only when the preferred provider is unavailable.

    Successful retains are mirrored locally. That means an outage after a
    successful incident save still leaves the current process with evidence for
    subsequent analyses, while Hindsight remains the source of truth whenever it
    is healthy.
    """

    def __init__(self, primary: MemoryProvider, fallback: MemoryProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name} -> {fallback.name} fallback"

    async def retain(self, payload: RetainPayload, document_id: str) -> str:
        await self.fallback.retain(payload, document_id)
        try:
            return await self.primary.retain(payload, document_id)
        except httpx.HTTPError as exc:
            logger.warning(
                "Primary memory provider '%s' failed while retaining '%s'; "
                "using local mirror: %s",
                self.primary.name,
                document_id,
                exc,
            )
            return document_id

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]:
        try:
            return await self.primary.recall(query)
        except httpx.HTTPError as exc:
            logger.warning(
                "Primary memory provider '%s' failed while recalling; using '%s': %s",
                self.primary.name,
                self.fallback.name,
                exc,
            )
            return await self.fallback.recall(query)

    async def get_mental_model(self, model_id: str) -> MentalModel | None:
        try:
            return await self.primary.get_mental_model(model_id)
        except httpx.HTTPError as exc:
            logger.warning(
                "Primary memory provider '%s' failed while reading a mental model; "
                "using '%s': %s",
                self.primary.name,
                self.fallback.name,
                exc,
            )
            return await self.fallback.get_mental_model(model_id)

    async def ensure_mental_model(
        self, model_id: str, name: str, source_query: str, tags: list[str]
    ) -> None:
        try:
            await self.primary.ensure_mental_model(model_id, name, source_query, tags)
        except httpx.HTTPError as exc:
            logger.warning(
                "Primary memory provider '%s' failed while creating a mental model; "
                "continuing with '%s': %s",
                self.primary.name,
                self.fallback.name,
                exc,
            )
        await self.fallback.ensure_mental_model(model_id, name, source_query, tags)

    async def clear(self) -> None:
        try:
            await self.primary.clear()
        except httpx.HTTPError as exc:
            await self.fallback.clear()
            raise ProviderUnavailableError(
                "The remote Hindsight bank could not be cleared. Sentinel cleared its "
                "local mirror but will not claim the demo has reset."
            ) from exc
        await self.fallback.clear()

    async def close(self) -> None:
        await self.primary.close()
        await self.fallback.close()
