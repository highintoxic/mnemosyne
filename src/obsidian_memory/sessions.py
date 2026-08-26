from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from .config import VaultConfig
from .ids import new_id
from .journal import Journal
from .notes import read_note, write_note
from .privacy import is_ignored, redact_sensitive
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
        metadata, current_body = read_note(path)
        activity = self._activity_lines(current_body)
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
        if activity:
            body += f"\n\n## Activity Log\n\n" + "\n".join(f"- {line}" for line in activity)
        write_note(path, metadata, body)
        for memory in overview.get("memories", []) if isinstance(overview.get("memories", []), list) else []:
            if not isinstance(memory, dict) or not memory.get("type") or not memory.get("title"):
                continue
            fields = dict(memory.get("fields", {}))
            fields["source_sessions"] = [path.stem]
            MemoryStore(self.vault).create_memory(str(memory["type"]), str(memory["title"]), str(memory.get("body", "")), fields)
        self.journal.append({"event": "session_finalized", "id": metadata["id"]})
        return path

    def finalize_auto(self, session: str, decisions: list[str] | None = None,
                      goals: list[str] | None = None, unresolved: list[str] | None = None,
                      follow_ups: list[str] | None = None) -> Path:
        """Build the overview from journal events recorded after session start."""
        path = self._find(session)
        if not path:
            raise FileNotFoundError(f"session not found: {session}")
        metadata, _ = read_note(path)
        started_at = str(metadata.get("created", ""))
        work: list[str] = []
        discoveries: list[str] = []
        journal_path = self.vault / ".memory/journal/events.jsonl"
        if journal_path.is_file():
            for line in journal_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict) or str(event.get("timestamp", "")) < started_at:
                    continue
                if event.get("event") == "memory_created":
                    note = self.vault / str(event.get("path", ""))
                    if note.suffix == ".md" and note.is_file():
                        try:
                            title = str(read_note(note)[0].get("title", note.stem))
                        except (OSError, ValueError):
                            title = note.stem
                        work.append(title)
                elif event.get("event") == "relation_created":
                    discoveries.append(f"{event.get('source')} {event.get('relation')} {event.get('target')}")
        overview: dict[str, object] = {
            "work": work or ["No memory writes recorded"],
            "discoveries": discoveries or [],
        }
        if goals:
            overview["goals"] = goals
        if decisions:
            overview["decisions"] = decisions
        if unresolved:
            overview["unresolved"] = unresolved
        if follow_ups:
            overview["follow_ups"] = follow_ups
        return self.finalize(session, overview)

    def update_activity(self, session: str, text: str) -> Path:
        """Append a timestamped, redacted activity entry to the session note."""
        path = self._find(session)
        if not path:
            raise FileNotFoundError(f"session not found: {session}")
        metadata, body = read_note(path)
        clean, _ = redact_sensitive(str(text), self.config.sensitive_patterns)
        if is_ignored(clean, tuple(self.config.ignore_markers)):
            return path
        entry = f"- {_now()} {clean}"
        marker = "## Activity Log"
        if marker in body:
            body = body.rstrip() + "\n" + entry + "\n"
        else:
            body = body.rstrip() + f"\n\n{marker}\n\n{entry}\n"
        write_note(path, metadata, body)
        self.journal.append({"event": "session_activity", "id": str(metadata.get("id", path.stem))})
        return path

    def _activity_lines(self, body: str) -> list[str]:
        """Extract existing Activity Log entries so finalize preserves them."""
        if "## Activity Log" not in body:
            return []
        section = body.split("## Activity Log", 1)[1]
        section = section.split("##", 1)[0]
        return [line.strip().lstrip("-").strip() for line in section.splitlines() if line.strip().startswith("-")]

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
