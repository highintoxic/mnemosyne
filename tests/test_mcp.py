from pathlib import Path

import pytest

from obsidian_memory.config import VaultConfig
from obsidian_memory.mcp import create_mcp_server


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
                "session_context", "review", "index", "doctor", "promote", "reject", "supersede"}
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
    from obsidian_memory.store import MemoryStore
    from obsidian_memory.mcp import _recall_impl
    
    store = MemoryStore(vault)
    store.create_memory("semantic", "Atomic writes", "Use atomic Markdown writes.", {"status": "active"})
    
    result = _recall_impl(vault, "atomic", limit=5)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all("id" in item and "title" in item and "type" in item for item in result)