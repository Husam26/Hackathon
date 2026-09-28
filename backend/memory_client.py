"""Memory provider abstraction with Hindsight and local implementations."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import quote

import httpx

from backend.schemas import MentalModel, RecallQuery, RecalledMemory, RetainPayload


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]+")


class MemoryProvider(Protocol):
    name: str

    async def retain(self, payload: RetainPayload, document_id: str) -> str: ...

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]: ...

    async def get_mental_model(self, model_id: str) -> MentalModel | None: ...

    async def ensure_mental_model(
        self, model_id: str, name: str, source_query: str, tags: list[str]
    ) -> None: ...

    async def clear(self) -> None: ...

    async def close(self) -> None: ...


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


class LocalMemoryClient:
    """In-process fallback for development and deterministic tests."""

    name = "local"

    def __init__(self) -> None:
        self._memories: dict[str, RecalledMemory] = {}

    async def retain(self, payload: RetainPayload, document_id: str) -> str:
        fact_type = "world" if "type:world-fact" in payload.tags else "experience"
        self._memories[document_id] = RecalledMemory(
            id=document_id,
            content=payload.content,
            tags=payload.tags,
            recall_score=1,
            timestamp=payload.timestamp,
            fact_type=fact_type,
        )
        return document_id

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]:
        query_tokens = _tokens(query.query)
        requested_types = set(query.fact_types)
        results: list[RecalledMemory] = []
        for memory in self._memories.values():
            if memory.fact_type not in requested_types:
                continue
            if query.tags and not set(query.tags).intersection(memory.tags):
                continue
            overlap = len(query_tokens & _tokens(memory.content)) / max(
                len(query_tokens), 1
            )
            tag_bonus = (
                0.2 if query.tags and set(query.tags).intersection(memory.tags) else 0
            )
            results.append(
                memory.model_copy(update={"recall_score": min(1, tag_bonus + overlap)})
            )
        return sorted(results, key=lambda item: item.recall_score, reverse=True)[
            : query.limit
        ]

    async def get_mental_model(self, model_id: str) -> MentalModel | None:
        matching = [
            memory
            for memory in self._memories.values()
            if "root-cause:redis-pool-exhaustion" in memory.tags
        ]
        if len(matching) < 2:
            return None
        return MentalModel(
            id=model_id,
            name="Checkout Redis exhaustion pattern",
            content=(
                "Repeated checkout-service latency and 5xx incidents follow payments-service "
                "deploys during the 02:00 UTC settlement window. Rolling back payments and "
                "restarting checkout has repeatedly mitigated the incident; JIRA-891 is the "
                "permanent fix."
            ),
            tags=["service:checkout-service", "root-cause:redis-pool-exhaustion"],
            last_refreshed_at=datetime.now(timezone.utc),
        )

    async def ensure_mental_model(
        self, model_id: str, name: str, source_query: str, tags: list[str]
    ) -> None:
        return None

    async def clear(self) -> None:
        self._memories.clear()

    async def close(self) -> None:
        return None


class HindsightMemoryClient:
    """Thin async wrapper around Hindsight Cloud's current REST API."""

    name = "hindsight"

    def __init__(
        self,
        *,
        base_url: str,
        bank_id: str,
        api_key: str | None,
        timeout: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.bank_id = bank_id
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    @property
    def _bank_path(self) -> str:
        return f"/v1/default/banks/{quote(self.bank_id, safe='')}"

    async def retain(self, payload: RetainPayload, document_id: str) -> str:
        item = {
            "content": payload.content,
            "context": payload.context,
            "timestamp": payload.timestamp.isoformat() if payload.timestamp else None,
            "document_id": document_id,
            "tags": payload.tags,
        }
        response = await self._client.post(
            f"{self._bank_path}/memories", json={"items": [item]}
        )
        response.raise_for_status()
        body = response.json()
        return str(body.get("operation_id") or body.get("id") or document_id)

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]:
        request_body = {
            "query": query.query,
            "tags": query.tags,
            "tags_match": "all_strict",
            "types": query.fact_types,
            "max_tokens": 4096,
        }
        for attempt in range(3):
            response = await self._client.post(
                f"{self._bank_path}/memories/recall", json=request_body
            )
            if response.status_code < 500 or attempt == 2:
                break
            await asyncio.sleep(0.25 * (attempt + 1))
        response.raise_for_status()
        memories: list[RecalledMemory] = []
        for item in response.json().get("results", [])[: query.limit]:
            scores = item.get("scores") or {}
            score = scores.get("final") or scores.get("reranker") or 0
            memories.append(
                RecalledMemory(
                    id=item.get("document_id") or item["id"],
                    content=item.get("text", ""),
                    tags=item.get("tags") or [],
                    recall_score=max(0, min(1, float(score))),
                    timestamp=item.get("occurred_start") or item.get("mentioned_at"),
                    fact_type=item.get("fact_type") or item.get("type"),
                )
            )
        return memories

    async def get_mental_model(self, model_id: str) -> MentalModel | None:
        for attempt in range(3):
            response = await self._client.get(
                f"{self._bank_path}/mental-models/{quote(model_id, safe='')}"
            )
            if response.status_code < 500 or attempt == 2:
                break
            await asyncio.sleep(0.25 * (attempt + 1))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        item = response.json()
        return MentalModel.model_validate(
            {
                "id": item["id"],
                "name": item["name"],
                "content": item.get("content"),
                "tags": item.get("tags") or [],
                "is_stale": item.get("is_stale", False),
                "last_refreshed_at": item.get("last_refreshed_at"),
            }
        )

    async def ensure_mental_model(
        self, model_id: str, name: str, source_query: str, tags: list[str]
    ) -> None:
        if await self.get_mental_model(model_id):
            return
        response = await self._client.post(
            f"{self._bank_path}/mental-models",
            json={
                "id": model_id,
                "name": name,
                "source_query": source_query,
                "tags": tags,
                "trigger": {"refresh_after_consolidation": True},
            },
        )
        response.raise_for_status()

    async def clear(self) -> None:
        response = await self._client.delete(f"{self._bank_path}/memories")
        if response.status_code != 404:
            response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()


async def retain_many(
    client: MemoryProvider, items: Iterable[tuple[RetainPayload, str]]
) -> list[str]:
    retained = []
    for payload, document_id in items:
        retained.append(await client.retain(payload, document_id))
    return retained
