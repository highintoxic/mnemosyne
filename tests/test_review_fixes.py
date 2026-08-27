from pathlib import Path
import json

from mnemosyne.config import VaultConfig
from mnemosyne.journal import Journal
from mnemosyne.notes import read_note
from mnemosyne.sessions import SessionStore
from mnemosyne.store import MemoryStore
from mnemosyne.maintenance import doctor
from mnemosyne.relations import RelationStore
from mnemosyne.retrieval import Retriever
from mnemosyne.cli import main as cli_main


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


TOKEN = "ghp_" + "A" * 30


def test_memory_title_is_redacted_in_frontmatter_and_filename(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    path = MemoryStore(tmp_path).create_memory("semantic", f"key is {TOKEN}", "body", {})
    assert TOKEN not in path.name
    assert TOKEN not in path.read_text(encoding="utf-8")


def test_entity_title_is_redacted_and_redactions_persist(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    path = MemoryStore(tmp_path).create_entity("project", f"proj {TOKEN}", {"description": f"desc {TOKEN}"})
    assert TOKEN not in path.name
    assert TOKEN not in path.read_text(encoding="utf-8")
    assert read_note(path)[0]["redactions"]


def test_superseded_memory_is_not_recalled(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    old = store.create_memory("semantic", "python version", "project uses python 3.11", {})
    store.supersede(old.stem, "semantic", "python version new", "project uses python 3.12", {})
    hits = Retriever(tmp_path).search("python version", limit=10)
    assert [hit["title"] for hit in hits] == ["python version new"]


def test_graph_expansion_respects_limit_without_extra_scans(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    alpha = store.create_memory("semantic", "alpha topic", "alpha alpha", {})
    beta = store.create_memory("semantic", "beta note", "unrelated words", {})
    RelationStore(tmp_path).add(alpha.stem, "supports", beta.stem)
    assert [hit["title"] for hit in Retriever(tmp_path).search("alpha", limit=1)] == ["alpha topic"]
    assert [hit["title"] for hit in Retriever(tmp_path).search("alpha", limit=5)] == ["alpha topic", "beta note"]


def test_cli_update_amends_memory_in_place(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    path = MemoryStore(tmp_path).create_memory("semantic", "Old", "old body", {})
    assert cli_main(["update", "--vault", str(tmp_path), "--id", path.stem, "--body", "new body", "--title", "New"]) == 0
    metadata, body = read_note(path)
    assert metadata["title"] == "New" and body == "new body"
