from pathlib import Path
import json

from mnemosyne.config import VaultConfig
from mnemosyne.journal import Journal
from mnemosyne.notes import read_note
from mnemosyne.sessions import SessionStore
from mnemosyne.store import MemoryStore
from mnemosyne.maintenance import doctor


def test_journal_attaches_explicit_session_id(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    journal = Journal(tmp_path / ".memory/journal/events.jsonl", session_id="session_a")
    journal.append({"event": "memory_created", "id": "mem_a"})
    event = json.loads(journal.path.read_text(encoding="utf-8"))
    assert event["session_id"] == "session_a"


def test_question_and_decision_auto_link_to_active_session(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    session = SessionStore(tmp_path).start("proj", None, None)
    session_id = (tmp_path / ".memory" / "current-session.txt").read_text().strip()
    store = MemoryStore(tmp_path)
    question = store.create_question("What?", "Answer", True, "topic", "easy")
    decision = store.create_decision("Choose A", "context", ["A"], "A", "because")
    assert read_note(question)[0]["source_sessions"] == [f"[[{session_id}]]"]
    assert read_note(decision)[0]["source_sessions"] == [f"[[{session_id}]]"]


def test_auto_finalize_ignores_events_from_other_session(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    first = SessionStore(tmp_path).start("proj", None, None)
    store = MemoryStore(tmp_path)
    first_memory = store.create_memory("semantic", "First", "first", {})
    second = SessionStore(tmp_path).start("proj", None, None)
    store.create_memory("semantic", "Second", "second", {})
    result = SessionStore(tmp_path).finalize_auto(first.stem)
    _, body = read_note(result)
    assert "First" in body
    assert "Second" not in body


def test_doctor_reports_unlinked_question_and_decision(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    store.create_question("Q", "A", True)
    store.create_decision("D", rationale="R")
    report = doctor(tmp_path)
    assert len(report["orphans"]) == 2


def test_entity_and_relation_link_to_active_session(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    SessionStore(tmp_path).start("proj", None, None)
    session_id = (tmp_path / ".memory" / "current-session.txt").read_text().strip()
    from mnemosyne.relations import RelationStore
    entity = MemoryStore(tmp_path).create_entity("project", "Alpha", {"description": "x"})
    relation = RelationStore(tmp_path).add("a", "related-to", "b")
    assert read_note(entity)[0]["source_sessions"] == [f"[[{session_id}]]"]
    assert read_note(relation)[0]["source_sessions"] == [f"[[{session_id}]]"]
