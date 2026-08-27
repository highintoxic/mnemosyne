"""Integration tests that exercise Mnemosyne's real runtime surfaces.

These tests drive the actual CLI binary, the real MCP server over stdio
JSON-RPC, and the real shell hooks, asserting behavior against the vault
on disk. They complement the in-process unit tests in the other modules.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mnemosyne.config import VaultConfig
from mnemosyne.journal import current_session_id
from mnemosyne.notes import read_note

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"


def _python() -> str:
    return sys.executable


def _run_cli(args: list[str], vault: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Invoke the real CLI as a subprocess (python -m mnemosyne.cli)."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [_python(), "-m", "mnemosyne.cli", *args, "--vault", str(vault)],
        capture_output=True, text=True, env=full_env,
    )


def _mnemosyne_on_path() -> str | None:
    """Return the current PATH if the mnemosyne console script is available."""
    if shutil.which("mnemosyne") is not None:
        return os.environ.get("PATH", "")
    return None


# ---------------------------------------------------------------------------
# CLI integration (real subprocess, real vault on disk)
# ---------------------------------------------------------------------------

def test_cli_init_save_recall_round_trip(tmp_path: Path):
    assert _run_cli(["init"], tmp_path).returncode == 0
    assert (tmp_path / ".memory" / "config.json").exists()

    save = _run_cli(
        ["save", "--type", "semantic", "--title", "Canonical store",
         "--body", "Markdown is the canonical, local-first store."],
        tmp_path,
    )
    assert save.returncode == 0, save.stderr
    note_path = Path(save.stdout.strip())
    assert note_path.exists()
    meta, body = read_note(note_path)
    assert meta["type"] == "semantic"
    assert "Markdown is the canonical" in body

    recall = _run_cli(["recall", "canonical store", "--json"], tmp_path)
    assert recall.returncode == 0, recall.stderr
    results = json.loads(recall.stdout)
    assert any(item["title"] == "Canonical store" for item in results)


def test_cli_save_supersede_creates_relation(tmp_path: Path):
    _run_cli(["init"], tmp_path)
    first = _run_cli(["save", "--type", "semantic", "--title", "Old", "--body", "old idea"], tmp_path)
    assert first.returncode == 0
    first_id = read_note(Path(first.stdout.strip()))[0]["id"]

    second = _run_cli(
        ["save", "--type", "semantic", "--title", "New", "--body", "new idea", "--supersede", first_id],
        tmp_path,
    )
    assert second.returncode == 0, second.stderr

    # The old note should be marked superseded.
    old_meta, _ = read_note(Path(first.stdout.strip()))
    assert old_meta["status"] == "superseded"
    # A relation note recording `supersedes` should exist.
    relations = list((tmp_path / "relations").glob("*.md"))
    assert relations, "expected a relation note"
    rel_meta, rel_body = read_note(relations[0])
    assert rel_meta["type"] == "relation"
    assert rel_meta["relation"] == "supersedes"
    # Relations link by note stem (like `source`), so wiki-links resolve in
    # Obsidian and retrieval can dedupe the superseded note against its hits.
    assert rel_meta["target"] == Path(first.stdout.strip()).stem


def test_cli_quiz_subprocess(tmp_path: Path):
    _run_cli(["init"], tmp_path)
    quiz = _run_cli(
        ["quiz", "--topic", "databases", "--score", "7", "--total", "10",
         "--weak-areas", "isolation", "--questions", "question_a", "question_b"],
        tmp_path,
    )
    assert quiz.returncode == 0, quiz.stderr
    meta, _ = read_note(Path(quiz.stdout.strip()))
    assert meta["type"] == "quiz" and meta["score"] == 7

    doctor = _run_cli(["doctor", "--json"], tmp_path)
    assert doctor.returncode == 0
    report = json.loads(doctor.stdout)
    assert "orphans" in report and "broken_links" in report


def test_cli_session_lifecycle_links_memories(tmp_path: Path):
    _run_cli(["init"], tmp_path)
    start = _run_cli(["session", "start", "--project", "proj-x"], tmp_path)
    assert start.returncode == 0
    session_id = current_session_id(tmp_path)
    assert session_id

    save = _run_cli(
        ["save", "--type", "semantic", "--title", "Linked fact", "--body", "observed during session"],
        tmp_path,
    )
    assert save.returncode == 0
    meta, _ = read_note(Path(save.stdout.strip()))
    # Auto-link resolves to the session note in Obsidian (wrapped note stem).
    assert meta["source_sessions"] == [f"[[{session_id}]]"]

    finalize = _run_cli(["session", "finalize", "--id", session_id, "--auto"], tmp_path)
    assert finalize.returncode == 0
    sessions = list((tmp_path / "sessions").glob("*.md"))
    fin_meta, fin_body = read_note(sessions[0])
    assert fin_meta["status"] == "complete"
    assert "Linked fact" in fin_body


# ---------------------------------------------------------------------------
# MCP server over real stdio JSON-RPC
# ---------------------------------------------------------------------------

def _mcp_proc(vault: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [_python(), "-m", "mnemosyne.mcp", str(vault)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )


def _mcp_send(proc: subprocess.Popen, method: str, params: dict | None = None, req_id: int = 1) -> dict:
    request = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        request["params"] = params
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)


def test_mcp_stdio_initialize_and_tools_list(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    proc = _mcp_proc(tmp_path)
    try:
        init = _mcp_send(proc, "initialize", {"protocolVersion": "2024-11-05"})
        assert init["jsonrpc"] == "2.0"
        assert init["result"]["serverInfo"]["name"] == "mnemosyne"

        listed = _mcp_send(proc, "tools/list")
        tools = {t["name"]: t for t in listed["result"]["tools"]}
        assert len(tools) == 17, f"expected 17 tools, got {len(tools)}"
        for name in ("save", "recall", "log_quiz", "session_finalize", "doctor"):
            assert name in tools, f"missing tool {name}"
            assert "inputSchema" in tools[name]
    finally:
        proc.terminate()


def test_mcp_stdio_save_then_recall(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    proc = _mcp_proc(tmp_path)
    try:
        _mcp_send(proc, "initialize", {})
        saved = _mcp_send(proc, "tools/call",
                          {"name": "save", "arguments": {"vault": str(tmp_path),
                                                         "type": "semantic", "title": "MCP memory",
                                                         "body": "created over the wire", "status": "active"}})
        assert saved["result"]["isError"] is False
        assert Path(saved["result"]["content"][0]["text"].strip()).exists()

        recalled = _mcp_send(proc, "tools/call",
                             {"name": "recall", "arguments": {"vault": str(tmp_path), "query": "wire memory"}})
        payload = json.loads(recalled["result"]["content"][0]["text"])
        assert any(item["title"] == "MCP memory" for item in payload)
    finally:
        proc.terminate()


def test_mcp_stdio_error_handling(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    proc = _mcp_proc(tmp_path)
    try:
        _mcp_send(proc, "initialize", {})
        # Missing required params -> tool returns isError True with a message.
        bad = _mcp_send(proc, "tools/call", {"name": "save", "arguments": {"vault": str(tmp_path)}})
        assert bad["result"]["isError"] is True
        assert "error" in bad["result"]["content"][0]["text"].lower()
        # Unknown method -> JSON-RPC error.
        unknown = _mcp_send(proc, "bogus/method")
        assert "error" in unknown
    finally:
        proc.terminate()


# ---------------------------------------------------------------------------
# Real shell hooks end-to-end (skipped if sh/mnemosyne unavailable)
# ---------------------------------------------------------------------------

def _hook_env(vault: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "MNEMOSYNE_VAULT": str(vault),
        "MNEMOSYNE_PROJECT": "proj-hook",
        "MNEMOSYNE_USER": "user-1",
        "MNEMOSYNE_AGENT": "agent-1",
        "MNEMOSYNE_LOG": str(vault / ".memory" / "hooks.log"),
    })
    path = _mnemosyne_on_path()
    if path:
        env["PATH"] = path
    return env


def _run_hook(name: str, vault: Path, stdin: str | None = None) -> subprocess.CompletedProcess:
    if shutil.which("sh") is None or shutil.which("mnemosyne") is None:
        pytest.skip("sh or mnemosyne console script not available")
    hook = HOOKS_DIR / name
    return subprocess.run(
        ["sh", str(hook)], input=stdin or "", capture_output=True, text=True,
        env=_hook_env(vault),
    )


def test_session_start_hook_creates_session(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    result = _run_hook("session-start.sh", tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".memory" / "current-session.txt").exists()
    assert list((tmp_path / "sessions").glob("*.md"))


def test_full_hook_workflow_links_and_finalizes(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    start = _run_hook("session-start.sh", tmp_path)
    assert start.returncode == 0

    session_note = next((tmp_path / "sessions").glob("*.md"))
    session_stem = session_note.stem

    # Every user prompt is logged as activity in the live session note.
    prompt = _run_hook("session-prompt.sh", tmp_path, stdin=json.dumps({"prompt": "write integration tests"}))
    assert prompt.returncode == 0, prompt.stderr
    _, body = read_note(session_note)
    assert "write integration tests" in body

    # A memory saved while the session is active auto-links back to it.
    save = _run_cli(["save", "--type", "semantic", "--title", "Hooked fact",
                     "--body", "captured via hook flow"], tmp_path)
    assert save.returncode == 0, save.stderr
    meta, _ = read_note(Path(save.stdout.strip()))
    assert meta["source_sessions"] == [f"[[{session_stem}]]"]

    # End hook finalizes the session and clears the marker.
    end = _run_hook("session-end.sh", tmp_path)
    assert end.returncode == 0
    assert not (tmp_path / ".memory" / "current-session.txt").exists()
    fin_meta, fin_body = read_note(session_note)
    assert fin_meta["status"] == "complete"
    assert "Hooked fact" in fin_body
