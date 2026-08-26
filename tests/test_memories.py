from mnemosyne.config import VaultConfig
from mnemosyne.notes import read_note
from mnemosyne.store import MemoryStore


def test_create_project_and_semantic_memory_links_entity(tmp_path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    project = store.create_entity("project", "Memory Workspace", {})
    memory = store.create_memory("semantic", "Canonical store", "Markdown is canonical.", {"entities": [project.stem]})
    metadata, body = read_note(memory)
    assert metadata["type"] == "semantic"
    assert f"[[{project.stem}]]" in metadata["entities"]
    assert body.startswith("Markdown")


def test_all_memory_types_are_supported(tmp_path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    for kind in ("semantic", "episodic", "procedural", "prospective", "parametric", "retrieval"):
        assert store.create_memory(kind, kind.title(), "content", {}) .is_file()
