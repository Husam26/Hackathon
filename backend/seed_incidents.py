"""Seed resolved incident history and world facts into the configured memory provider."""

import asyncio
from pathlib import Path

from backend.config import get_settings
from backend.main import build_services
from backend.schemas import IncidentCorpus, RetainPayload


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "incidents.json"


async def seed() -> None:
    settings = get_settings()
    services = build_services(settings)
    corpus = IncidentCorpus.model_validate_json(DATA_FILE.read_text(encoding="utf-8"))
    try:
        for incident in corpus.incidents:
            await services.orchestrator.resolve(incident)
        for index, fact in enumerate(corpus.world_facts, start=1):
            await services.memory.retain(
                RetainPayload(content=fact.content, tags=fact.tags), f"WORLD-{index}"
            )
        await services.memory.ensure_mental_model(
            settings.hindsight_mental_model_id,
            "Checkout Redis exhaustion pattern",
            "What recurring checkout Redis incidents, triggers, mitigations, and unresolved fixes exist?",
            ["service:checkout-service", "root-cause:redis-pool-exhaustion"],
        )
        print(
            f"Seeded {len(corpus.incidents)} incidents and {len(corpus.world_facts)} world facts."
        )
    finally:
        await services.memory.close()
        await services.analyzer.close()


if __name__ == "__main__":
    asyncio.run(seed())
