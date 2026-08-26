from pathlib import Path

import pytest

from obsidian_memory.config import VaultConfig
from obsidian_memory.notes import read_note
from obsidian_memory.relations import RelationStore
from obsidian_memory.sessions import SessionStore
from obsidian_memory.store import MemoryStore


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    VaultConfig.initialize(tmp_path)
    return tmp_path


def test_promote_and_reject_change_status(vault: Path):
    store = MemoryStore(vault)
    memory = store.create_memory("semantic", "Draft claim", "A draft.", {})
    promoted = store.set_status(memory.stem, "active")
    assert read_note(promoted)[0]["status"] == "active"
    rejected = store.set_status(promoted.stem, "rejected")
    assert read_note(rejected)[0]["status"] == "rejected"


def test_set_status_rejects_unknown_status(vault: Path):
    store = MemoryStore(vault)
    memory = store.create_memory("semantic", "Claim", "Body.", {})
    with pytest.raises(ValueError):
        store.set_status(memory.stem, "bogus")


def test_supersede_marks_old_and_links_new(vault: Path):
    store = MemoryStore(vault)
    old = store.create_memory("semantic", "Old fact", "Python 3.11 is required.", {"status": "active"})
    new = store.supersede(old.stem, kind="semantic", title="Updated fact", body="Python 3.12 is required.")
    assert read_note(old)[0]["status"] == "superseded"
    new_meta = read_note(new)[0]
    assert new_meta["status"] == "candidate"
    relations = list((vault / "relations").glob("*.md"))
    assert any(read_note(r)[0].get("relation") == "supersedes" and read_note(r)[0].get("source") == new.stem for r in relations)


def test_supersede_missing_old_note_fails(vault: Path):
    store = MemoryStore(vault)
    with pytest.raises(FileNotFoundError):
        store.supersede("missing_id", kind="semantic", title="X", body="Y")


def test_link_fields_written_as_wiki_links(vault: Path):
    store = MemoryStore(vault)
    project = store.create_entity("project", "Graph Project", {})
    session = SessionStore(vault).start(project.stem, None, None)
    memory = store.create_memory("semantic", "Linked claim", "Body.", {
        "entities": [project.stem],
        "source_sessions": [session.stem],
        "related": ["mem_other"],
    })
    meta = read_note(memory)[0]
    assert meta["entities"] == [f"[[{project.stem}]]"]
    assert meta["source_sessions"] == [f"[[{session.stem}]]"]
    assert meta["related"] == ["[[mem_other]]"]


def test_self_relation_rejected(vault: Path):
    store = MemoryStore(vault)
    memory = store.create_memory("semantic", "Solo", "Body.", {})
    identifier = read_note(memory)[0]["id"]
    with pytest.raises(ValueError, match="self-relation"):
        RelationStore(vault).add(identifier, "related-to", identifier)


def test_update_memory_amends_in_place(vault: Path):
    store = MemoryStore(vault)
    memory = store.create_memory("semantic", "Claim", "Old body.", {"confidence": 0.5})
    identifier = read_note(memory)[0]["id"]
    store.update_memory(identifier, body="New body.", confidence=0.9)
    meta, body = read_note(memory)
    assert body == "New body."
    assert meta["confidence"] == 0.9
    assert meta["status"] == "candidate"  # status preserved
    assert meta["updated"] != meta["created"]


def test_update_memory_missing_note_fails(vault: Path):
    store = MemoryStore(vault)
    with pytest.raises(FileNotFoundError):
        store.update_memory("missing_id", body="X")
