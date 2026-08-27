from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

# Harness-provided identifiers for "the session this process belongs to", tried
# in order. Without one, the vault falls back to a single global marker, which
# is correct for one session at a time but lets concurrent sessions overwrite
# each other.
SESSION_ENV_KEYS = ("MNEMOSYNE_SESSION_KEY", "CLAUDE_CODE_SESSION_ID")
LEGACY_MARKER = "current-session.txt"


def session_key() -> str | None:
    for name in SESSION_ENV_KEYS:
        value = os.environ.get(name, "").strip()
        if value:
            return re.sub(r"[^A-Za-z0-9._-]+", "-", value)[:120]
    return None


def marker_paths(vault: Path) -> list[Path]:
    """Markers to consult, most specific first."""
    memory = Path(vault) / ".memory"
    key = session_key()
    paths = [memory / "sessions" / f"{key}.txt"] if key else []
    return paths + [memory / LEGACY_MARKER]


def write_marker(vault: Path, session_stem: str) -> None:
    """Record the active session for this process and, for harnesses with no
    session id of their own, globally."""
    for path in marker_paths(vault):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(session_stem, encoding="utf-8")


def clear_marker(vault: Path, session_stem: str) -> None:
    """Drop only the markers that point at this session."""
    for path in marker_paths(vault):
        try:
            if path.read_text(encoding="utf-8").strip() == session_stem:
                path.unlink()
        except OSError:
            continue


def current_session_id(vault: Path) -> str | None:
    """Read only the most specific marker. Falling back to the global one when a
    session key exists would hand this process whichever session started last --
    the exact misattribution per-session markers are here to prevent."""
    try:
        value = marker_paths(vault)[0].read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


class Journal:
    def __init__(self, path: Path, session_id: str | None = None):
        self.path = Path(path)
        self.session_id = session_id

    def append(self, event: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
        effective_session = self.session_id or current_session_id(self.path.parent.parent.parent)
        if effective_session and "session_id" not in payload:
            payload["session_id"] = effective_session
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()
