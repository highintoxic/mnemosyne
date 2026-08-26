from pathlib import Path

import pytest

from obsidian_memory.config import VaultConfig
from obsidian_memory.providers import TfidfProvider
from obsidian_memory.retrieval import Retriever
from obsidian_memory.store import MemoryStore


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    VaultConfig.initialize(tmp_path)
    return tmp_path


def _documents(vault: Path) -> list[dict[str, object]]:
    return [
        {"id": "doc_atomic", "text": "atomic writes atomic commits ensure durability"},
        {"id": "doc_gardening", "text": "watering tomatoes requires sunlight and patience"},
    ]


def test_tfidf_ranks_relevant_document_first():
    provider = TfidfProvider()
    results = provider.search("atomic writes", _documents(vault=Path(".")), limit=2)
    assert results[0]["id"] == "doc_atomic"
    assert results[0]["score"] > results[1]["score"]


def test_tfidf_ignores_documents_without_overlap():
    provider = TfidfProvider()
    results = provider.search("quantum flux capacitor", _documents(vault=Path(".")), limit=2)
    assert all(item["score"] == 0 for item in results)


def test_retriever_blends_provider_scores(vault: Path):
    store = MemoryStore(vault)
    strong = store.create_memory("semantic", "Atomic writes", "Use atomic Markdown writes with replace operations. Atomicity matters.", {"status": "active"})
    store.create_memory("procedural", "Gardening", "Water tomatoes with patience.", {"status": "active"})
    retriever = Retriever(vault, provider=TfidfProvider())
    results = retriever.search("atomic write operations", limit=5)
    assert results[0]["id"] == strong.stem
