"""Gemini analysis adapter and provider failover support."""

from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from backend.groq_client import IncidentAnalyzer
from backend.schemas import Alert, MentalModel, RecalledMemory, SentinelResponse


logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are Sentinel, an SRE Incident Commander. Return JSON only. Reason only from "
    "retrieved_memory and the mental_model. Never invent incident IDs, fixes, tickets, "
    "or history. If the match is weak or empty, classify NOVEL and provide generic triage. "
    "Every historical claim must cite an ID present in retrieved_memory."
)


class GeminiAnalyzer:
    """Gemini REST adapter that preserves Sentinel's response contract."""

    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"x-goog-api-key": api_key},
            timeout=timeout,
            transport=transport,
        )

    async def analyze(
        self,
        alert: Alert,
        memories: list[RecalledMemory],
        mental_model: MentalModel | None,
    ) -> SentinelResponse:
        allowed_ids = {memory.id for memory in memories}
        prompt = {
            "current_alert": alert.model_dump(mode="json"),
            "retrieved_memory": [memory.model_dump(mode="json") for memory in memories],
            "mental_model": mental_model.model_dump(mode="json")
            if mental_model
            else None,
            "output_schema": SentinelResponse.model_json_schema(),
        }
        contents = [{"role": "user", "parts": [{"text": json.dumps(prompt)}]}]
        last_error: Exception | None = None
        for _ in range(2):
            response = await self._client.post(
                f"/models/{self.model}:generateContent",
                json={
                    "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json",
                    },
                },
            )
            response.raise_for_status()
            parts = (
                response.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            content = "".join(part.get("text", "") for part in parts)
            try:
                result = SentinelResponse.model_validate_json(content)
                cited = set(result.cited_memory_ids)
                hypothesis_citations = {
                    item
                    for hypothesis in result.hypotheses
                    for item in hypothesis.based_on_memory_ids
                }
                if not cited.issubset(allowed_ids) or not hypothesis_citations.issubset(
                    allowed_ids
                ):
                    raise ValueError("model cited memory IDs that were not retrieved")
                return result
            except (ValidationError, ValueError) as exc:
                last_error = exc
                contents.append({"role": "model", "parts": [{"text": content}]})
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"Correct the JSON and citation contract: {exc}"}
                        ],
                    }
                )
        raise RuntimeError(
            "Gemini returned an invalid grounded response"
        ) from last_error

    async def close(self) -> None:
        await self._client.aclose()


class FallbackAnalyzer:
    """Runs the backup only when the primary provider cannot return a valid answer."""

    def __init__(self, primary: IncidentAnalyzer, fallback: IncidentAnalyzer) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name} -> {fallback.name} fallback"

    async def analyze(
        self,
        alert: Alert,
        memories: list[RecalledMemory],
        mental_model: MentalModel | None,
    ) -> SentinelResponse:
        try:
            return await self.primary.analyze(alert, memories, mental_model)
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.warning(
                "Primary analysis provider '%s' failed; using '%s': %s",
                self.primary.name,
                self.fallback.name,
                exc,
            )
            return await self.fallback.analyze(alert, memories, mental_model)

    async def close(self) -> None:
        await self.primary.close()
        await self.fallback.close()
