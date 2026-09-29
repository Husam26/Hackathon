"""Sentinel's alert-to-memory-to-analysis orchestration loop."""

from backend.groq_client import IncidentAnalyzer
from backend.memory_client import MemoryProvider
from backend.memory_preferences import MemoryPreferences
from backend.schemas import (
    Alert,
    AnalysisResult,
    IncidentRecord,
    MemoryImpact,
    RecallQuery,
    RecalledMemory,
)
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

    async def analyze(
        self, alert: Alert, preferences: MemoryPreferences | None = None
    ) -> AnalysisResult:
        selected = preferences or MemoryPreferences()
        base_tags = [f"service:{alert.service}"]
        severity_tags = selected.severity_tags() or [None]
        recalled: dict[str, RecalledMemory] = {}
        for severity_tag in severity_tags:
            query = RecallQuery(
                query=self.build_query(alert),
                tags=base_tags + ([severity_tag] if severity_tag else []),
                fact_types=["experience", "world", "observation"],
                limit=8,
                temporal_window=selected.temporal_window(alert.fired_at),
            )
            for memory in await self.memory.recall(query):
                existing = recalled.get(memory.id)
                if existing is None or memory.recall_score > existing.recall_score:
                    recalled[memory.id] = memory
        memories = sorted(
            recalled.values(), key=lambda memory: memory.recall_score, reverse=True
        )[:8]
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
            memory_impact=MemoryImpact(
                recalled_count=len(memories),
                grounded_citation_count=len(response.cited_memory_ids),
                highest_relevance=memories[0].recall_score if memories else None,
                temporal_bias_applied=selected.recency != "all_history",
                severity_tags_applied=selected.severity_tags(),
            ),
        )

    async def resolve(self, incident: IncidentRecord) -> str:
        memory_id = await self.memory.retain(incident.retain, incident.id)
        self.store.upsert(incident, memory_id)
        return memory_id
