"""Concurrent sessions must not steal each other's memories.

The vault used to keep one global `.memory/current-session.txt`, so whichever
session started last owned every memory written by every session.
"""
from pathlib import Path

from mnemosyne.cli import main as cli_main
from mnemosyne.config import VaultConfig
from mnemosyne.journal import current_session_id
from mnemosyne.notes import read_note
from mnemosyne.sessions import SessionStore
from mnemosyne.store import MemoryStore


def test_concurrent_sessions_keep_their_own_memories(tmp_path: Path, monkeypatch):
    VaultConfig.initialize(tmp_path)

    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-aaa")
    first = SessionStore(tmp_path).start("project-a", None, None)

    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-bbb")
    second = SessionStore(tmp_path).start("project-b", None, None)

    # Session A saves *after* session B started -- the old global marker would
    # have handed this memory to B.
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-aaa")
    memory_a = MemoryStore(tmp_path).create_memory("semantic", "from a", "body a", {})
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-bbb")
    memory_b = MemoryStore(tmp_path).create_memory("semantic", "from b", "body b", {})

    assert read_note(memory_a)[0]["source_sessions"] == [f"[[{first.stem}]]"]
    assert read_note(memory_b)[0]["source_sessions"] == [f"[[{second.stem}]]"]


def test_session_key_falls_back_to_the_global_marker(tmp_path: Path, monkeypatch):
    """Harnesses that expose no session id keep the original behaviour."""
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("MNEMOSYNE_SESSION_KEY", raising=False)
    VaultConfig.initialize(tmp_path)
    session = SessionStore(tmp_path).start(None, None, None)
    assert (tmp_path / ".memory" / "current-session.txt").read_text().strip() == session.stem
    assert current_session_id(tmp_path) == session.stem


def test_finalize_clears_only_its_own_marker(tmp_path: Path, monkeypatch):
    VaultConfig.initialize(tmp_path)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-aaa")
    first = SessionStore(tmp_path).start(None, None, None)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-bbb")
    second = SessionStore(tmp_path).start(None, None, None)

    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-aaa")
    SessionStore(tmp_path).finalize_auto(first.stem)
    assert current_session_id(tmp_path) is None

    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-bbb")
    assert current_session_id(tmp_path) == second.stem


def test_cli_session_current_prints_the_active_session(tmp_path: Path, monkeypatch, capsys):
    VaultConfig.initialize(tmp_path)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "harness-ccc")
    session = SessionStore(tmp_path).start(None, None, None)
    capsys.readouterr()
    assert cli_main(["session", "current", "--vault", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == session.stem
