"""Application composition root for Sentinel's runtime dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from backend.config import Settings
from backend.demo import DemoController
from backend.gemini_client import FallbackAnalyzer, GeminiAnalyzer
from backend.groq_client import GroqAnalyzer, IncidentAnalyzer, RulesAnalyzer
from backend.memory_client import (
    HindsightMemoryClient,
    LocalMemoryClient,
    MemoryProvider,
)
from backend.orchestrator import SentinelOrchestrator
from backend.resilience import FallbackMemoryProvider
from backend.store import IncidentStore


@dataclass
class Services:
    """Long-lived dependencies owned by one FastAPI application instance."""

    settings: Settings
    memory: MemoryProvider
    analyzer: IncidentAnalyzer
    store: IncidentStore
    orchestrator: SentinelOrchestrator
    demo: DemoController

    async def close(self) -> None:
        """Close external clients in the reverse order of request use."""
        await self.analyzer.close()
        await self.memory.close()


def build_memory(settings: Settings) -> MemoryProvider:
    if not (
        settings.hindsight_api_key
        or settings.hindsight_base_url.startswith("http://localhost")
    ):
        return LocalMemoryClient()
    hindsight = HindsightMemoryClient(
        base_url=settings.hindsight_base_url,
        bank_id=settings.hindsight_bank_id,
        api_key=settings.hindsight_api_key,
        timeout=settings.request_timeout_seconds,
    )
    return FallbackMemoryProvider(hindsight, LocalMemoryClient())


def build_analyzer(settings: Settings) -> IncidentAnalyzer:
    groq = (
        GroqAnalyzer(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            timeout=settings.request_timeout_seconds,
        )
        if settings.groq_api_key
        else None
    )
    gemini = (
        GeminiAnalyzer(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            base_url=settings.gemini_base_url,
            timeout=settings.request_timeout_seconds,
        )
        if settings.gemini_api_key
        else None
    )
    rules = RulesAnalyzer()
    if groq and gemini:
        return FallbackAnalyzer(FallbackAnalyzer(groq, gemini), rules)
    if groq:
        return FallbackAnalyzer(groq, rules)
    if gemini:
        return FallbackAnalyzer(gemini, rules)
    return rules


def build_services(settings: Settings) -> Services:
    """Build the dependency graph once at application startup."""
    memory = build_memory(settings)
    analyzer = build_analyzer(settings)
    store = IncidentStore(settings.database_url)
    store.create()
    orchestrator = SentinelOrchestrator(
        memory, analyzer, store, settings.hindsight_mental_model_id
    )
    return Services(
        settings=settings,
        memory=memory,
        analyzer=analyzer,
        store=store,
        orchestrator=orchestrator,
        demo=DemoController(orchestrator),
    )
