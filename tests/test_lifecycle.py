from pathlib import Path

import pytest

from obsidian_memory.config import VaultConfig
from obsidian_memory.relations import RelationStore
from obsidian_memory.store import MemoryStore
from obsidian_memory.notes import read_note


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
