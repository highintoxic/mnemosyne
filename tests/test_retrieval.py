from mnemosyne.config import VaultConfig
from mnemosyne.relations import RelationStore
from mnemosyne.retrieval import Retriever
from mnemosyne.store import MemoryStore


def test_recall_matches_text_and_expands_related_notes(tmp_path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    first = store.create_memory("semantic", "Atomic writes", "Use atomic Markdown writes.", {})
    second = store.create_memory("procedural", "Write workflow", "Write a temporary file then replace it.", {})
    RelationStore(tmp_path).add(first.stem, "implements", second.stem)
    results = Retriever(tmp_path).search("atomic Markdown", limit=5)
    ids = {item["id"] for item in results}
    assert first.stem in ids
    assert second.stem in ids
