from obsidian_memory.config import VaultConfig
from obsidian_memory.notes import read_note
from obsidian_memory.sessions import SessionStore
from obsidian_memory.store import MemoryStore


def test_finalize_session_contains_required_sections(tmp_path):
    VaultConfig.initialize(tmp_path)
    sessions = SessionStore(tmp_path)
    path = sessions.start("project_1", "user_1", "agent_1")
    sessions.finalize(path.stem, {"goals": ["ship"], "decisions": ["use Markdown"], "work": ["implemented"], "discoveries": [], "unresolved": ["provider choice"], "follow_ups": []})
    _, body = read_note(path)
    for heading in ("## Goals", "## Decisions", "## Work", "## Discoveries", "## Unresolved Questions", "## Follow-ups"):
        assert heading in body


def test_finalize_extracts_source_linked_candidate_memories(tmp_path):
    VaultConfig.initialize(tmp_path)
    sessions = SessionStore(tmp_path)
    path = sessions.start("project_1", "user_1", "agent_1")
    sessions.finalize(path.stem, {
        "memories": [{"type": "semantic", "title": "Canonical storage", "body": "Markdown is canonical."}],
    })
    memories = list((tmp_path / "memories/semantic").glob("*.md"))
    assert len(memories) == 1
    metadata, _ = read_note(memories[0])
    assert metadata["status"] == "candidate"
    assert f"[[{path.stem}]]" in metadata["source_sessions"]


def test_session_redacts_sensitive_request_and_context(tmp_path):
    VaultConfig.initialize(tmp_path)
    sessions = SessionStore(tmp_path)
    path = sessions.start(None, None, None)
    sessions.finalize(path.stem, {
        "initial_request": "Use token=ghp_abcdefghijklmnopqrstuvwxyz123456",
        "context": ["Bearer abcdefghijklmnopqrstuvwxyz"],
    })
    _, body = read_note(path)
    assert "ghp_" not in body
    assert "Bearer abc" not in body
