from pathlib import Path

from backend.schemas import IncidentCorpus
from backend.store import IncidentStore


ROOT = Path(__file__).resolve().parents[2]


def test_store_upserts_and_clears_incidents(tmp_path: Path) -> None:
    corpus = IncidentCorpus.model_validate_json(
        (ROOT / "data" / "incidents.json").read_text(encoding="utf-8")
    )
    incident = corpus.incidents[0]
    store = IncidentStore(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    store.create()

    store.upsert(incident, "memory-1")
    store.upsert(incident, "memory-2")

    assert [item.id for item in store.list()] == [incident.id]
    stored = store.get(incident.id)
    assert stored is not None
    assert stored.id == incident.id
    assert stored.retained_memory_id == "memory-2"
    store.clear()
    assert store.list() == []
