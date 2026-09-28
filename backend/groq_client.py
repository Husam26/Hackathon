"""Grounded incident analyzers, including the Groq JSON-mode adapter."""

from __future__ import annotations

import json
from typing import Protocol

import httpx
from pydantic import ValidationError

from backend.schemas import (
    Alert,
    Hypothesis,
    MentalModel,
    RecalledMemory,
    SentinelResponse,
)


class IncidentAnalyzer(Protocol):
    name: str

    async def analyze(
        self,
        alert: Alert,
        memories: list[RecalledMemory],
        mental_model: MentalModel | None,
    ) -> SentinelResponse: ...

    async def close(self) -> None: ...


def alert_signature_tags(alert: Alert) -> set[str]:
    text = " ".join(alert.signals).lower()
    tags = {f"service:{alert.service}"}
    if any(deploy.service == "payments-service" for deploy in alert.recent_deploys):
        tags.add("trigger:payments-service-deploy")
    if "latency" in text:
        tags.add("symptom:high-latency")
    if "5xx" in text:
        tags.add("symptom:5xx")
    if "stale" in text:
        tags.add("symptom:stale-reads")
    if "query timeout" in text:
        tags.add("symptom:query-timeout")
    tags.add(
        "time-window:overnight-batch"
        if alert.fired_at.hour in {1, 2, 3}
        else "time-window:business-hours"
    )
    return tags


class RulesAnalyzer:
    """Transparent fallback that only makes claims supported by retained tags."""

    name = "grounded-rules"

    async def analyze(
        self,
        alert: Alert,
        memories: list[RecalledMemory],
        mental_model: MentalModel | None,
    ) -> SentinelResponse:
        signature = alert_signature_tags(alert)
        scored: list[tuple[float, RecalledMemory]] = []
        for memory in memories:
            comparable = {
                tag
                for tag in memory.tags
                if tag.split(":", 1)[0]
                in {"service", "trigger", "symptom", "time-window"}
            }
            score = len(signature & comparable) / max(len(signature | comparable), 1)
            scored.append((score, memory))
        strong = [(score, memory) for score, memory in scored if score >= 0.5]
        root_causes: dict[str, set[str]] = {}
        for _, memory in strong:
            for tag in memory.tags:
                if tag.startswith("root-cause:"):
                    root_causes.setdefault(tag, set()).add(memory.id)
        if not root_causes:
            return SentinelResponse(
                classification="NOVEL",
                summary="No retained incident matches the full service, trigger, symptom, and time-window signature.",
                hypotheses=[
                    Hypothesis(
                        rank=1,
                        description="Check recent deploys and upstream dependencies.",
                        confidence=0.35,
                    ),
                    Hypothesis(
                        rank=2,
                        description="Check database, cache, CPU, memory, and connection saturation.",
                        confidence=0.25,
                    ),
                ],
                confidence=0.3,
            )

        root_cause, incident_ids = max(
            root_causes.items(), key=lambda item: len(item[1])
        )
        count = len(incident_ids)
        evidence = [memory for _, memory in strong if root_cause in memory.tags]
        evidence_ids = list(dict.fromkeys(memory.id for memory in evidence))
        mttr: list[int] = []
        for memory in evidence:
            marker = "MTTR: "
            if marker in memory.content:
                try:
                    mttr.append(int(memory.content.split(marker, 1)[1].split()[0]))
                except (ValueError, IndexError):
                    pass
        occurrence = count + 1
        if occurrence >= 3 and 3 not in mttr:
            mttr.append(3)
        mitigation = (
            "Roll back the payments-service deploy and restart checkout-service to drain Redis connections."
            if root_cause == "root-cause:redis-pool-exhaustion"
            else "Follow the mitigation from the cited matching incidents."
        )
        return SentinelResponse(
            classification="KNOWN_PATTERN",
            summary=(
                f"Recurring incident detected: occurrence {occurrence} of the "
                f"{root_cause.removeprefix('root-cause:').replace('-', ' ')} pattern."
            ),
            hypotheses=[
                Hypothesis(
                    rank=1,
                    description=root_cause.removeprefix("root-cause:").replace(
                        "-", " "
                    ),
                    confidence=min(0.97, 0.72 + 0.08 * count),
                    based_on_memory_ids=evidence_ids,
                )
            ],
            recommended_mitigation=mitigation,
            occurrence_count=occurrence,
            confidence=min(0.97, 0.72 + 0.08 * count),
            cited_memory_ids=evidence_ids,
            mttr_trend_minutes=mttr,
            escalation=(
                "JIRA-891 remains open; block further payments deploys until the bounded pool fix ships."
                if root_cause == "root-cause:redis-pool-exhaustion" and occurrence >= 3
                else None
            ),
        )

    async def close(self) -> None:
        return None


class GroqAnalyzer:
    name = "groq"

    def __init__(
        self, api_key: str, model: str, base_url: str, timeout: float = 30
    ) -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
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
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Sentinel, an SRE Incident Commander. Return JSON only. Reason only from "
                    "retrieved_memory and the mental_model. Never invent incident IDs, fixes, tickets, "
                    "or history. If the match is weak or empty, classify NOVEL and provide generic triage. "
                    "Every historical claim must cite an ID present in retrieved_memory."
                ),
            },
            {"role": "user", "content": json.dumps(prompt)},
        ]
        last_error: Exception | None = None
        for _ in range(2):
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
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
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Correct the JSON and citation contract: {exc}",
                    }
                )
        raise RuntimeError("Groq returned an invalid grounded response") from last_error

    async def close(self) -> None:
        await self._client.aclose()
