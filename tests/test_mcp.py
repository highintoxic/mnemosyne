from pathlib import Path

import pytest

from mnemosyne.config import VaultConfig
from mnemosyne.mcp import create_mcp_server


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    VaultConfig.initialize(tmp_path)
    return tmp_path


def test_mcp_server_creates_tools(vault: Path):
    """MCP server should expose all memory operations as tools."""
    server = create_mcp_server(vault)
    tools = server.list_tools()
    tool_names = {t.name for t in tools}
    expected = {"init", "save", "recall", "entity", "session_start", "session_finalize", 
                "session_context", "session_update", "update", "review", "index", "doctor", "promote", "reject", "supersede",
                "log_question", "log_decision"}
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


def test_mcp_tool_schema_has_required_params(vault: Path):
    """Each tool should have a proper JSON schema with required params."""
    server = create_mcp_server(vault)
    save_tool = next(t for t in server.list_tools() if t.name == "save")
    schema = save_tool.inputSchema
    assert schema["type"] == "object"
    assert "type" in schema["required"]
    assert "title" in schema["required"]
    assert "body" in schema["required"]


def test_mcp_recall_returns_structured_results(vault: Path):
    """recall tool should return structured results an agent can use."""
    from mnemosyne.store import MemoryStore
    from mnemosyne.mcp import _recall_impl
    
    store = MemoryStore(vault)
    store.create_memory("semantic", "Atomic writes", "Use atomic Markdown writes.", {"status": "active"})
    
    result = _recall_impl(vault, "atomic", limit=5)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all("id" in item and "title" in item and "type" in item for item in result)


def test_save_auto_links_to_active_session(vault: Path):
    """save should auto-attach source_sessions when a session is active."""
    from mnemosyne.sessions import SessionStore
    from mnemosyne.mcp import _fields_with_session
    from mnemosyne.notes import read_note
    
    sessions = SessionStore(vault)
    session = sessions.start("proj", None, None)
    # persist the marker the start hook writes
    (vault / ".memory/current-session.txt").write_text(session.stem, encoding="utf-8")
    
    fields = _fields_with_session({"type": "semantic", "title": "Linked", "body": "B."}, vault)
    assert fields["source_sessions"] == [session.stem]
    
    # and create_memory actually writes it as a wiki-link
    from mnemosyne.store import MemoryStore
    path = MemoryStore(vault).create_memory("semantic", "Linked", "B.", fields)
    meta, _ = read_note(path)
    assert meta["source_sessions"] == [f"[[{session.stem}]]"]


def test_no_active_session_means_no_auto_link(vault: Path):
    from mnemosyne.mcp import _fields_with_session
    fields = _fields_with_session({"type": "semantic", "title": "T", "body": "B."}, vault)
    assert "source_sessions" not in fields