from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from .config import VaultConfig
from .ids import new_id
from .journal import Journal
from .notes import read_note, write_note
from .privacy import redact_sensitive
from .store import MemoryStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _items(values: object) -> str:
    if values is None:
        return "- None recorded"
    if isinstance(values, str):
        values = [values]
    return "\n".join(f"- {value}" for value in values) or "- None recorded"


class SessionStore:
    def __init__(self, vault: Path):
        self.config = VaultConfig.load(Path(vault))
        self.vault = self.config.vault
        self.journal = Journal(self.vault / ".memory/journal/events.jsonl")

    def start(self, project: str | None, user: str | None, agent: str | None) -> Path:
        identifier = new_id("session")
        path = self.vault / "sessions" / f"{datetime.now().strftime('%Y-%m-%d')}-{identifier}.md"
        links = {"project": project, "user": user, "agent": agent}
        metadata = {"memory_schema": 1, "id": identifier, "type": "session", "title": path.stem,
                    "status": "active", "created": _now(), "updated": _now(),
                    **{key: (f"[[{value}]]" if value else None) for key, value in links.items()}}
        body = "# Session Overview\n\n## Initial Request\n\n- Not recorded\n\n## Context Loaded\n\n- None recorded\n\n## Goals\n\n- None recorded\n\n## Decisions\n\n- None recorded\n\n## Work\n\n- None recorded\n\n## Discoveries\n\n- None recorded\n\n## Unresolved Questions\n\n- None recorded\n\n## Follow-ups\n\n- None recorded\n\n## Extracted Memories\n\n- None recorded\n"
        write_note(path, metadata, body)
        self.journal.append({"event": "session_started", "id": identifier})
        return path

    def finalize(self, session: str, overview: dict[str, object]) -> Path:
        path = self._find(session)
        if not path:
            raise FileNotFoundError(f"session not found: {session}")
        metadata, _ = read_note(path)
        metadata.update({"status": "complete", "updated": _now()})
        sections = [("Goals", overview.get("goals", [])), ("Decisions", overview.get("decisions", [])),
                    ("Work", overview.get("work", [])), ("Discoveries", overview.get("discoveries", [])),
                    ("Unresolved Questions", overview.get("unresolved", [])), ("Follow-ups", overview.get("follow_ups", [])),
                    ("Extracted Memories", overview.get("memories", []))]
        body = "# Session Overview\n\n"
        def clean_values(values: object) -> list[str]:
            raw = values if isinstance(values, list) else [values]
            cleaned = []
            for value in raw:
                text, _ = redact_sensitive(str(value), self.config.sensitive_patterns)
                cleaned.append(text)
            return cleaned
        body += "## Initial Request\n\n" + _items(clean_values(overview.get("initial_request"))) + "\n\n"
        body += "## Context Loaded\n\n" + _items(clean_values(overview.get("context"))) + "\n\n"
        for heading, values in sections:
            clean = []
            for value in (values if isinstance(values, list) else [values]):
                text, _ = redact_sensitive(str(value), self.config.sensitive_patterns)
                clean.append(text)
            body += f"## {heading}\n\n{_items(clean)}\n\n"
        body += "## Related Sessions\n\n" + _items(clean_values(overview.get("related_sessions")))
        write_note(path, metadata, body)
        for memory in overview.get("memories", []) if isinstance(overview.get("memories", []), list) else []:
            if not isinstance(memory, dict) or not memory.get("type") or not memory.get("title"):
                continue
            fields = dict(memory.get("fields", {}))
            fields["source_sessions"] = [path.stem]
            MemoryStore(self.vault).create_memory(str(memory["type"]), str(memory["title"]), str(memory.get("body", "")), fields)
        self.journal.append({"event": "session_finalized", "id": metadata["id"]})
        return path

    def load_context(self, project: str | None, limit: int = 10) -> list[dict[str, object]]:
        found = []
        for path in self.vault.joinpath("sessions").glob("*.md"):
            try:
                metadata, body = read_note(path)
            except (OSError, ValueError):
                continue
            if project and project not in str(metadata.get("project", "")):
                continue
            found.append({"id": metadata.get("id", path.stem), "title": metadata.get("title", path.stem),
                          "path": str(path.relative_to(self.vault)), "type": "session", "excerpt": body[:500]})
        return found[:limit]

    def _find(self, identifier: str) -> Path | None:
        for path in self.vault.joinpath("sessions").glob("*.md"):
            if path.stem == identifier:
                return path
            try:
                metadata, _ = read_note(path)
            except (OSError, ValueError):
                continue
            if metadata.get("id") == identifier:
                return path
        return None
