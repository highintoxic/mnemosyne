from pathlib import Path
import json
import shutil
import subprocess
import sys

from mnemosyne.config import VaultConfig
from mnemosyne.journal import current_session_id
from mnemosyne.maintenance import doctor
from mnemosyne.notes import read_note
from mnemosyne.sessions import SessionStore
from mnemosyne.store import MemoryStore


def test_quiz_records_score_and_links(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    SessionStore(tmp_path).start("proj", None, None)
    session_id = current_session_id(tmp_path)
    quiz = MemoryStore(tmp_path).create_quiz("databases", 7, 10, ["isolation"], ["question_a", "question_b"])
    meta = read_note(quiz)[0]
    assert meta["type"] == "quiz"
    assert meta["score"] == 7 and meta["total"] == 10
    assert meta["weak_areas"] == ["isolation"]
    assert meta["questions"] == ["[[question_a]]", "[[question_b]]"]
    assert meta["source_sessions"] == [f"[[{session_id}]]"]


def test_concurrent_sessions_separate_journals(tmp_path: Path):
    VaultConfig.initialize(tmp_path)
    first = SessionStore(tmp_path).start("proj", None, None)
    first_id = current_session_id(tmp_path)
    store = MemoryStore(tmp_path)
    store.create_memory("semantic", "First", "first", {})
    SessionStore(tmp_path).start("proj", None, None)  # switches active session
    store.create_question("Second Q", "ans", True)
    # Finalize first session: should include "First" only.
    result = SessionStore(tmp_path).finalize_auto(first.stem)
    _, body = read_note(result)
    assert "First" in body
    assert "Second Q" not in body


def test_prompt_json_parsing_handles_quotes_and_newlines():
    payload = json.dumps({"prompt": 'explain "atomic writes" and {"a": 1}\nnext line'}).encode()
    code = (
        "import json, sys\n"
        "try:\n    data = json.load(sys.stdin)\n"
        "except (json.JSONDecodeError, OSError):\n    data = {}\n"
        "print(str(data.get('prompt', ''))[:2000])"
    )
    proc = subprocess.run([sys.executable, "-c", code], input=payload, capture_output=True)
    assert proc.returncode == 0
    assert 'explain "atomic writes" and {"a": 1}' in proc.stdout.decode()
    # Malformed input should not crash.
    bad = subprocess.run([sys.executable, "-c", code], input=b"not json", capture_output=True)
    assert bad.returncode == 0
    assert bad.stdout.decode().strip() == ""


def test_prompt_hook_runs_fail_open(tmp_path: Path):
    hook = Path(__file__).resolve().parent.parent / "hooks" / "session-prompt.sh"
    if not hook.exists() or shutil.which("sh") is None:
        return
    env = {**__import__("os").environ, "MNEMOSYNE_VAULT": str(tmp_path)}
    VaultConfig.initialize(tmp_path)
    proc = subprocess.run(["sh", str(hook)], input='{"prompt":"hello world"}',
                          capture_output=True, env=env, text=True)
    assert proc.returncode == 0
    assert (tmp_path / ".memory/current-session.txt").exists()
