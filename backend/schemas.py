"""Validated contracts shared across Sentinel's API and provider adapters."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecentDeploy(StrictModel):
    service: str = Field(min_length=1)
    version: str = Field(min_length=1)
    at: datetime


class Alert(StrictModel):
    service: str = Field(min_length=1)
    fired_at: datetime
    severity: Literal["SEV-1", "SEV-2", "SEV-3", "SEV-4"]
    metrics: dict[str, float] = Field(default_factory=dict)
    signals: list[str] = Field(default_factory=list)
    recent_deploys: list[RecentDeploy] = Field(default_factory=list)


class TimelineEvent(StrictModel):
    at: str = Field(min_length=1)
    event: str = Field(min_length=1)


class PermanentFix(StrictModel):
    status: Literal["open", "in_progress", "done"]
    ref: str = Field(min_length=1)
    desc: str = Field(min_length=1)


class Artifacts(StrictModel):
    pr: str | None = None
    runbook: str | None = None
    jira: str | None = None


class RetainPayload(StrictModel):
    content: str = Field(min_length=1)
    context: str | None = None
    timestamp: datetime | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def tags_are_unique(cls, tags: list[str]) -> list[str]:
        if len(tags) != len(set(tags)):
            raise ValueError("tags must be unique")
        return tags


class IncidentRecord(StrictModel):
    id: str = Field(pattern=r"^INC-\d+$")
    seq: int = Field(ge=1)
    title: str = Field(min_length=1)
    is_recurring_spine: bool = False
    alert: Alert
    timeline: list[TimelineEvent] = Field(default_factory=list)
    root_cause: str | None = None
    contributing_factors: list[str] = Field(default_factory=list)
    mitigation: str | None = None
    permanent_fix: PermanentFix | None = None
    mttr_minutes: int | None = Field(default=None, ge=0)
    artifacts: Artifacts = Field(default_factory=Artifacts)
    retain: RetainPayload
    retained_memory_id: str | None = None


class WorldFact(StrictModel):
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class IncidentCorpus(StrictModel):
    company: str = Field(min_length=1)
    bank_id: str = Field(min_length=1)
    incidents: list[IncidentRecord] = Field(min_length=1)
    world_facts: list[WorldFact] = Field(default_factory=list)

    @field_validator("incidents")
    @classmethod
    def incidents_have_unique_ids_and_sequences(
        cls, incidents: list[IncidentRecord]
    ) -> list[IncidentRecord]:
        ids = [incident.id for incident in incidents]
        sequences = [incident.seq for incident in incidents]
        if len(ids) != len(set(ids)):
            raise ValueError("incident ids must be unique")
        if len(sequences) != len(set(sequences)):
            raise ValueError("incident sequences must be unique")
        return incidents


class RecalledMemory(StrictModel):
    id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    recall_score: float = Field(ge=0, le=1)
    timestamp: datetime | None = None
    fact_type: Literal["world", "experience", "observation"] | None = None
    retrieval_scores: dict[str, float] = Field(default_factory=dict)


class RecallQuery(StrictModel):
    query: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    fact_types: list[Literal["world", "experience", "observation"]] = Field(
        default_factory=lambda: ["experience", "world"]
    )
    limit: int = Field(default=5, ge=1, le=20)
    temporal_window: dict[str, str] | None = None


class MentalModel(StrictModel):
    id: str
    name: str
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_stale: bool = False
    last_refreshed_at: datetime | None = None


class Hypothesis(StrictModel):
    rank: int = Field(ge=1)
    description: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    based_on_memory_ids: list[str] = Field(default_factory=list)


class SentinelResponse(StrictModel):
    classification: Literal["KNOWN_PATTERN", "NOVEL"]
    summary: str = Field(min_length=1)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    recommended_mitigation: str | None = None
    occurrence_count: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0, le=1)
    cited_memory_ids: list[str] = Field(default_factory=list)
    mttr_trend_minutes: list[int] = Field(default_factory=list)
    escalation: str | None = None


class MemoryImpact(StrictModel):
    recalled_count: int = Field(default=0, ge=0)
    grounded_citation_count: int = Field(default=0, ge=0)
    highest_relevance: float | None = Field(default=None, ge=0, le=1)
    temporal_bias_applied: bool = False
    severity_tags_applied: list[str] = Field(default_factory=list)


class AnalysisResult(StrictModel):
    alert: Alert
    response: SentinelResponse
    recalled_memories: list[RecalledMemory] = Field(default_factory=list)
    mental_model: MentalModel | None = None
    memory_impact: MemoryImpact = Field(default_factory=MemoryImpact)


class ResolveIncidentRequest(StrictModel):
    incident: IncidentRecord


class HealthResponse(StrictModel):
    status: Literal["ok", "degraded"]
    version: str
    providers: dict[str, str]


JsonObject = dict[str, Any]
