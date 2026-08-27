from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path


def current_session_id(vault: Path) -> str | None:
    try:
        value = (Path(vault) / ".memory" / "current-session.txt").read_text(encoding="utf-8").strip()
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
