from pathlib import Path

import pytest

from obsidian_memory.config import VaultConfig
from obsidian_memory.notes import read_note
from obsidian_memory.sessions import SessionStore
from obsidian_memory.store import MemoryStore


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    VaultConfig.initialize(tmp_path)
    return tmp_path


def test_auto_finalize_collects_work_from_journal(vault: Path):
    store = MemoryStore(vault)
    sessions = SessionStore(vault)
    session = sessions.start("proj", None, None)
    store.create_memory("semantic", "Atomic writes", "Use atomic writes.", {})
    store.create_memory("procedural", "Write workflow", "Temp file then replace.", {})
    result = sessions.finalize_auto(session.stem, decisions=["stay canonical"])
    _, body = read_note(result)
    assert "## Work" in body
    assert "Atomic writes" in body
    assert "Write workflow" in body
    assert "- stay canonical" in body
    assert read_note(result)[0]["status"] == "complete"


def test_auto_finalize_missing_session_fails(vault: Path):
    with pytest.raises(FileNotFoundError):
        SessionStore(vault).finalize_auto("missing_session")
