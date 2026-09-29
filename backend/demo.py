"""Deterministic controller for replaying the five-incident learning curve."""

import json
from pathlib import Path

from pydantic import BaseModel

from backend.memory_preferences import MemoryPreferences
from backend.orchestrator import SentinelOrchestrator
from backend.schemas import AnalysisResult, IncidentCorpus, IncidentRecord


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "incidents.json"


class DemoStepResult(BaseModel):
    step: int
    total_steps: int
    incident: IncidentRecord
    analysis: AnalysisResult


class DemoStatus(BaseModel):
    position: int
    total_steps: int
    next_incident_id: str | None


class DemoController:
    def __init__(self, orchestrator: SentinelOrchestrator) -> None:
        self.orchestrator = orchestrator
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.corpus = IncidentCorpus.model_validate(payload)
        self.incidents = sorted(
            (incident for incident in self.corpus.incidents if incident.seq <= 5),
            key=lambda incident: incident.seq,
        )
        self.position = 0

    def status(self) -> DemoStatus:
        next_incident = (
            self.incidents[self.position]
            if self.position < len(self.incidents)
            else None
        )
        return DemoStatus(
            position=self.position,
            total_steps=len(self.incidents),
            next_incident_id=next_incident.id if next_incident else None,
        )

    async def reset(self) -> None:
        await self.orchestrator.memory.clear()
        self.orchestrator.store.clear()
        self.position = 0

    async def step(
        self, preferences: MemoryPreferences | None = None
    ) -> DemoStepResult:
        if self.position >= len(self.incidents):
            raise IndexError("demo is complete; reset before requesting another step")
        incident = self.incidents[self.position]
        analysis = await self.orchestrator.analyze(incident.alert, preferences)
        await self.orchestrator.resolve(incident)
        self.position += 1
        return DemoStepResult(
            step=self.position,
            total_steps=len(self.incidents),
            incident=incident,
            analysis=analysis,
        )
