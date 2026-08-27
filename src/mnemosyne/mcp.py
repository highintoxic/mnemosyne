"""Minimal MCP (Model Context Protocol) stdio server for the memory workspace.

Zero external dependencies: implements just enough JSON-RPC 2.0 over stdio to
serve ``initialize``, ``tools/list`` and ``tools/call``, which is all an MCP
client needs to discover and invoke memory operations. Works with Claude Code,
Codex, Cursor, Gemini CLI, and any other MCP-capable harness.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from .config import VaultConfig
from .maintenance import doctor, rebuild_index, review
from .providers import TfidfProvider
from .relations import RelationStore
from .retrieval import Retriever
from .sessions import SessionStore
from .store import MemoryStore

DEFAULT_VAULT = Path(os.environ.get("MNEMOSYNE_VAULT", "C:/Memory"))


class Tool:
    def __init__(self, name: str, description: str, input_schema: dict[str, Any], handler: Callable[[dict[str, Any]], Any]):
        self.name = name
        self.description = description
        self.inputSchema = input_schema
        self._handler = handler

    def call(self, arguments: dict[str, Any]) -> Any:
        return self._handler(arguments)


class MCPMemoryServer:
    """Exposes the memory workspace as MCP tools."""

    def __init__(self, vault: Path):
        self.vault = Path(vault)
        self.tools: dict[str, Tool] = {}
        self._register_tools()

    def list_tools(self) -> list[Tool]:
        return list(self.tools.values())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self.tools:
            raise KeyError(f"unknown tool: {name}")
        return self.tools[name].call(arguments or {})

    # -- tool registry ---------------------------------------------------

    def _tool(self, name: str, description: str, schema: dict[str, Any], handler: Callable[[dict[str, Any]], Any]) -> None:
        self.tools[name] = Tool(name, description, schema, handler)

    def _register_tools(self) -> None:
        str_param = lambda required: {"type": "string", "description": required}
        vault_param = {"type": "string", "description": "Vault path override", "default": str(DEFAULT_VAULT)}

        def _store(args: dict[str, Any]) -> MemoryStore:
            return MemoryStore(Path(args.get("vault", str(self.vault))))

        def _sessions(args: dict[str, Any]) -> SessionStore:
            return SessionStore(Path(args.get("vault", str(self.vault))))

        self._tool("init", "Initialize a memory vault with the default layout",
                   {"type": "object", "properties": {"vault": vault_param}},
                   lambda a: str(VaultConfig.initialize(Path(a.get("vault", str(self.vault))))))

        self._tool("save", "Save a typed memory note",
                   {"type": "object", "required": ["type", "title", "body"],
                    "properties": {"vault": vault_param, "type": str_param("memory type: semantic, episodic, procedural, prospective, parametric, retrieval"),
                                   "title": str_param("short title"), "body": str_param("claim or record"),
                                   "status": {"type": "string", "default": "candidate"},
                                   "confidence": {"type": "number", "default": 0.5},
                                   "importance": {"type": "number", "default": 0.5},
                                   "entities": {"type": "array", "items": {"type": "string"}, "description": "entity IDs to link"},
                                   "source_sessions": {"type": "array", "items": {"type": "string"}},
                                   "related": {"type": "array", "items": {"type": "string"}},
                                   "supersede": {"type": "string", "description": "old note ID this supersedes"}}},
                   lambda a: str(_store(a).supersede(a["supersede"], a["type"], a["title"], a["body"], _fields_with_session(a, Path(a.get("vault", str(self.vault)))))
                                 if a.get("supersede") else _store(a).create_memory(a["type"], a["title"], a["body"], _fields_with_session(a, Path(a.get("vault", str(self.vault)))))))

        self._tool("recall", "Retrieve relevant memory context",
                   {"type": "object", "required": ["query"],
                    "properties": {"vault": vault_param, "query": str_param("search text"),
                                   "type": {"type": "string"}, "limit": {"type": "integer", "default": 10},
                                   "semantic": {"type": "boolean", "default": False, "description": "blend TF-IDF ranking"}}},
                   lambda a: _recall_impl(Path(a.get("vault", str(self.vault))), a["query"],
                                          a.get("type"), a.get("limit", 10), bool(a.get("semantic", False))))

        self._tool("entity", "Create a user, project, or agent entity",
                   {"type": "object", "required": ["kind", "title"],
                    "properties": {"vault": vault_param, "kind": {"type": "string", "enum": ["user", "person", "project", "agent"]},
                                   "title": str_param("entity name"), "description": {"type": "string", "default": ""}}},
                   lambda a: str(_store(a).create_entity(a["kind"], a["title"], {"description": a.get("description", "").strip()})))

        self._tool("session_start", "Start a session and record its project/user/agent context",
                   {"type": "object", "properties": {"vault": vault_param, "project": str_param("project ID"), "user": str_param("user ID"), "agent": str_param("agent ID")}},
                   lambda a: str(_sessions(a).start(a.get("project"), a.get("user"), a.get("agent"))))

        self._tool("session_finalize", "Finalize a session with an overview (or --auto from the journal)",
                   {"type": "object", "required": ["session_id"],
                    "properties": {"vault": vault_param, "session_id": str_param("session note ID"),
                                   "overview": {"type": "string", "description": "JSON overview string"},
                                   "auto": {"type": "boolean", "default": False, "description": "build overview from journal"},
                                   "decisions": {"type": "array", "items": {"type": "string"}}}},
                   lambda a: str(_finalize_impl(_sessions(a), a["session_id"], a.get("overview"), bool(a.get("auto", False)), a.get("decisions"))))

        self._tool("session_context", "Load recent session context for a project",
                   {"type": "object", "properties": {"vault": vault_param, "project": str_param("project ID"), "limit": {"type": "integer", "default": 10}}},
                   lambda a: _sessions(a).load_context(a.get("project"), a.get("limit", 10)))

        self._tool("session_update", "Append a timestamped activity entry to the active session",
                   {"type": "object", "required": ["session_id", "text"],
                    "properties": {"vault": vault_param, "session_id": str_param("session note ID"), "text": str_param("activity entry")}},
                   lambda a: str(_sessions(a).update_activity(a["session_id"], a["text"])))

        self._tool("update", "Amend an existing memory in place (body/title/confidence)",
                   {"type": "object", "required": ["id"],
                    "properties": {"vault": vault_param, "id": str_param("note ID"),
                                   "body": str_param("new body"), "title": str_param("new title"),
                                   "confidence": {"type": "number"}, "importance": {"type": "number"}}},
                   lambda a: str(_update_impl(_store(a), a)))

        self._tool("log_question", "Record a quiz/learning question with answer and correctness",
                   {"type": "object", "required": ["question", "answer"],
                    "properties": {"vault": vault_param, "question": str_param("the question asked"),
                                   "answer": str_param("the answer"), "correct": {"type": "boolean", "default": True},
                                   "topic": str_param("subject area"), "difficulty": str_param("easy/medium/hard")}},
                   lambda a: str(_store(a).create_question(a["question"], a["answer"], bool(a.get("correct", True)),
                                                          a.get("topic"), a.get("difficulty"))))

        self._tool("log_decision", "Record a decision with context, options, choice, and rationale",
                   {"type": "object", "required": ["decision", "rationale"],
                    "properties": {"vault": vault_param, "decision": str_param("the decision made"),
                                   "context": str_param("situation"), "options": {"type": "array", "items": {"type": "string"}},
                                   "chosen": str_param("what was chosen"), "rationale": str_param("why")}},
                   lambda a: str(_store(a).create_decision(a["decision"], a.get("context", ""), a.get("options"),
                                                          a.get("chosen"), a["rationale"])))

        self._tool("log_quiz", "Record a graded quiz batch (score, topic, weak areas, linked questions)",
                   {"type": "object", "required": ["topic", "score", "total"],
                    "properties": {"vault": vault_param, "topic": str_param("subject area"),
                                   "score": {"type": "integer"}, "total": {"type": "integer"},
                                   "weak_areas": {"type": "array", "items": {"type": "string"}},
                                   "questions": {"type": "array", "items": {"type": "string"}}}},
                   lambda a: str(_store(a).create_quiz(a["topic"], int(a["score"]), int(a["total"]),
                                                      a.get("weak_areas"), a.get("questions"))))

        self._tool("promote", "Promote a candidate memory to active",
                   {"type": "object", "required": ["id"], "properties": {"vault": vault_param, "id": str_param("note ID")}},
                   lambda a: str(_store(a).set_status(a["id"], "active")))

        self._tool("reject", "Reject a candidate memory",
                   {"type": "object", "required": ["id"], "properties": {"vault": vault_param, "id": str_param("note ID")}},
                   lambda a: str(_store(a).set_status(a["id"], "rejected")))

        self._tool("supersede", "Mark a note superseded by a new one (creates the relation)",
                   {"type": "object", "required": ["old_id", "type", "title", "body"],
                    "properties": {"vault": vault_param, "old_id": str_param("note to supersede"),
                                   "type": str_param("new memory type"), "title": str_param("new title"), "body": str_param("new body")}},
                   lambda a: str(_store(a).supersede(a["old_id"], a["type"], a["title"], a["body"])))

        self._tool("review", "List candidates, stale notes, contradictions, and duplicates",
                   {"type": "object", "properties": {"vault": vault_param}},
                   lambda a: review(Path(a.get("vault", str(self.vault)))))

        self._tool("index", "Rebuild the disposable search index",
                   {"type": "object", "properties": {"vault": vault_param}},
                   lambda a: str(rebuild_index(Path(a.get("vault", str(self.vault))))))

        self._tool("doctor", "Diagnose vault consistency (broken links, orphans, etc.)",
                   {"type": "object", "properties": {"vault": vault_param}},
                   lambda a: doctor(Path(a.get("vault", str(self.vault)))))


def _fields(args: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in ("status", "confidence", "importance"):
        if key in args:
            fields[key] = args[key]
    for key in ("entities", "source_sessions", "related"):
        if key in args:
            fields[key] = args[key]
    return fields


def active_session_id(vault: Path) -> str | None:
    """Return the active session ID from the current-session marker, if any."""
    marker = Path(vault) / ".memory/current-session.txt"
    try:
        value = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _fields_with_session(args: dict[str, Any], vault: Path) -> dict[str, Any]:
    fields = _fields(args)
    if "source_sessions" not in fields:
        active = active_session_id(vault)
        if active:
            fields["source_sessions"] = [active]
    return fields


def _update_impl(store: MemoryStore, args: dict[str, Any]) -> Any:
    kwargs: dict[str, Any] = {}
    for key in ("body", "title", "confidence", "importance"):
        if key in args and args[key] is not None:
            kwargs[key] = args[key]
    return store.update_memory(args["id"], **kwargs)


def _finalize_impl(sessions: SessionStore, session_id: str, overview: str | None,
                   auto: bool, decisions: list[str] | None) -> Any:
    if auto:
        return sessions.finalize_auto(session_id, decisions=decisions)
    payload = json.loads(overview) if overview else {}
    return sessions.finalize(session_id, payload)


def _recall_impl(vault: Path, query: str, type_filter: str | None = None,
                 limit: int = 10, semantic: bool = False) -> list[dict[str, Any]]:
    filters = {"type": type_filter} if type_filter else None
    provider = TfidfProvider() if semantic else None
    return Retriever(vault, provider=provider).search(query, filters, limit)


def create_mcp_server(vault: Path) -> MCPMemoryServer:
    """Factory used by tests and embedders."""
    return MCPMemoryServer(vault)


# -- stdio JSON-RPC loop (MCP wire protocol) --------------------------------

def _jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _text_content(value: Any) -> dict[str, Any]:
    return {"type": "text", "text": value if isinstance(value, str) else json.dumps(value, indent=2, default=str)}


def run_stdio_server(vault: Path) -> int:
    server = MCPMemoryServer(vault)
    initialized = False
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            initialized = True
            sys.stdout.write(json.dumps(_jsonrpc_result(request_id, {
                "protocolVersion": message.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "mnemosyne", "version": "0.1.0"},
            })) + "\n")
            sys.stdout.flush()
        elif method == "notifications/initialized" or method == "notifications/initialized/notifications":
            continue
        elif method == "ping":
            sys.stdout.write(json.dumps(_jsonrpc_result(request_id, {})) + "\n")
            sys.stdout.flush()
        elif method == "tools/list":
            tools = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                     for t in server.list_tools()]
            sys.stdout.write(json.dumps(_jsonrpc_result(request_id, {"tools": tools})) + "\n")
            sys.stdout.flush()
        elif method == "tools/call":
            params = message.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                result = server.call_tool(name, arguments)
                payload = _jsonrpc_result(request_id, {"content": [_text_content(result)], "isError": False})
            except (KeyError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
                payload = _jsonrpc_result(request_id, {"content": [_text_content(f"error: {exc}")], "isError": True})
            sys.stdout.write(json.dumps(payload) + "\n")
            sys.stdout.flush()
        else:
            if request_id is not None:
                sys.stdout.write(json.dumps(_jsonrpc_error(request_id, -32601, f"method not found: {method}")) + "\n")
                sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    vault = Path(args[0]) if args else DEFAULT_VAULT
    return run_stdio_server(vault)


if __name__ == "__main__":
    raise SystemExit(main())
