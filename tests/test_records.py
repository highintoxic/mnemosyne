from pathlib import Path

import pytest

from mnemosyne.config import VaultConfig
from mnemosyne.notes import read_note
from mnemosyne.store import MemoryStore


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    VaultConfig.initialize(tmp_path)
    return tmp_path


def test_question_record_has_structured_fields(vault: Path):
    store = MemoryStore(vault)
    path = store.create_question(
        question="What is atomicity?",
        answer="All-or-nothing execution",
        correct=True,
        topic="databases",
        difficulty="easy",
    )
    meta, body = read_note(path)
    assert meta["type"] == "question"
    assert meta["question"] == "What is atomicity?"
    assert meta["answer"] == "All-or-nothing execution"
    assert meta["correct"] is True
    assert meta["topic"] == "databases"
    assert meta["difficulty"] == "easy"
    assert meta["status"] == "active"
    assert path.parent.name == "questions"


def test_incorrect_question_record(vault: Path):
    store = MemoryStore(vault)
    path = store.create_question("2+2?", "5", correct=False, topic="math", difficulty="easy")
    meta, _ = read_note(path)
    assert meta["correct"] is False


def test_decision_record_has_context_and_rationale(vault: Path):
    store = MemoryStore(vault)
    path = store.create_decision(
        decision="Use Markdown as canonical store",
        context="Need portable, inspectable memory",
        options=["Database", "Markdown"],
        chosen="Markdown",
        rationale="Portable and human-readable; no sync conflicts",
    )
    meta, body = read_note(path)
    assert meta["type"] == "decision"
    assert meta["decision"] == "Use Markdown as canonical store"
    assert meta["options"] == ["Database", "Markdown"]
    assert meta["chosen"] == "Markdown"
    assert meta["rationale"].startswith("Portable")
    assert path.parent.name == "decisions"


def test_question_requires_answer(vault: Path):
    store = MemoryStore(vault)
    with pytest.raises(ValueError):
        store.create_question(question="Q?", answer="", correct=True, topic="t", difficulty="easy")


def test_decision_requires_rationale(vault: Path):
    store = MemoryStore(vault)
    with pytest.raises(ValueError):
        store.create_decision(decision="D", context="c", options=[], chosen="D", rationale="")


def test_question_and_decision_redact_secrets(vault: Path):
    store = MemoryStore(vault)
    q = store.create_question("token?", "ghp_abcdefghijklmnopqrstuvwxyz123456", correct=True, topic="t", difficulty="easy")
    d = store.create_decision("D", "context", ["a"], "a", "Bearer abcdefghijklmnopqrstuvwxyz")
    assert "ghp_" not in read_note(q)[1]
    assert "Bearer abc" not in read_note(d)[1]
