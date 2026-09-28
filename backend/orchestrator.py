"""Sentinel's alert-to-memory-to-analysis orchestration loop."""

from backend.groq_client import IncidentAnalyzer
from backend.memory_client import MemoryProvider
from backend.schemas import Alert, AnalysisResult, IncidentRecord, RecallQuery
from backend.store import IncidentStore


class SentinelOrchestrator:
    def __init__(
        self,
        memory: MemoryProvider,
        analyzer: IncidentAnalyzer,
        store: IncidentStore,
        mental_model_id: str,
    ) -> None:
        self.memory = memory
        self.analyzer = analyzer
        self.store = store
        self.mental_model_id = mental_model_id

    @staticmethod
    def build_query(alert: Alert) -> str:
        deploys = (
            ", ".join(
                f"{item.service} {item.version} at {item.at.isoformat()}"
                for item in alert.recent_deploys
            )
            or "none"
        )
        return (
            f"{alert.service} {alert.severity} at {alert.fired_at.isoformat()}; "
            f"signals: {', '.join(alert.signals)}; recent deploys: {deploys}"
        )

    async def analyze(self, alert: Alert) -> AnalysisResult:
        memories = await self.memory.recall(
            RecallQuery(
                query=self.build_query(alert),
                tags=[f"service:{alert.service}"],
                fact_types=["experience", "world", "observation"],
                limit=8,
            )
        )
        mental_model = (
            await self.memory.get_mental_model(self.mental_model_id)
            if len(memories) >= 2
            else None
        )
        response = await self.analyzer.analyze(alert, memories, mental_model)
        return AnalysisResult(
            alert=alert,
            response=response,
            recalled_memories=memories,
            mental_model=mental_model,
        )

    async def resolve(self, incident: IncidentRecord) -> str:
        memory_id = await self.memory.retain(incident.retain, incident.id)
        self.store.upsert(incident, memory_id)
        return memory_id
