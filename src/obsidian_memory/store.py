from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re

from .config import VaultConfig
from .ids import new_id
from .journal import Journal
from .notes import read_note, write_note
from .privacy import is_ignored, redact_sensitive

ENTITY_DIRS = {"user": "users", "person": "users", "project": "projects", "agent": "agents"}
MEMORY_TYPES = {"semantic", "episodic", "procedural", "prospective", "parametric", "retrieval"}
VALID_STATUSES = {"candidate", "active", "superseded", "archived", "rejected"}


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _link(identifier: str) -> str:
    return identifier if identifier.startswith("[[") else f"[[{identifier}]]"


class MemoryStore:
    def __init__(self, vault: Path):
        self.config = VaultConfig.load(Path(vault))
        self.vault = self.config.vault
        self.journal = Journal(self.vault / ".memory/journal/events.jsonl")

    def create_entity(self, kind: str, title: str, fields: dict[str, object]) -> Path:
        fields = dict(fields)
        folder = ENTITY_DIRS.get(kind.lower())
        if not folder:
            raise ValueError(f"unsupported entity kind: {kind}")
        identifier = new_id(kind)
        path = self.vault / "entities" / folder / f"{slugify(title)}-{identifier}.md"
        description = fields.pop("description", "")
        description, findings = redact_sensitive(str(description), self.config.sensitive_patterns)
        if is_ignored(description, tuple(self.config.ignore_markers)):
            raise ValueError("entity capture is excluded")
        metadata = {"memory_schema": 1, "id": identifier, "type": kind.lower(), "title": title,
                    "status": fields.pop("status", "active"), "created": _now(), "updated": _now(), **fields}
        write_note(path, metadata, f"# {title}\n\n{description}".rstrip())
        if findings:
            metadata["redactions"] = findings
        self.journal.append({"event": "entity_created", "id": identifier, "path": str(path.relative_to(self.vault))})
        return path

    def create_memory(self, kind: str, title: str, body: str, fields: dict[str, object]) -> Path:
        fields = dict(fields)
        kind = kind.lower()
        if kind not in MEMORY_TYPES:
            raise ValueError(f"unsupported memory type: {kind}")
        if self.config.is_path_excluded(self.vault / "memories" / kind) or is_ignored(body, tuple(self.config.ignore_markers)):
            raise ValueError("memory capture is excluded")
        clean, findings = redact_sensitive(body, self.config.sensitive_patterns)
        identifier = new_id("mem")
        path = self.vault / "memories" / kind / f"{slugify(title)}-{identifier}.md"
        metadata = {"memory_schema": 1, "id": identifier, "type": kind, "title": title,
                    "status": fields.pop("status", "candidate"), "created": _now(), "updated": _now(),
                    "confidence": fields.pop("confidence", 0.5), "importance": fields.pop("importance", 0.5),
                    "tags": fields.pop("tags", [f"memory/{kind}"]), **fields}
        write_note(path, metadata, clean)
        self.journal.append({"event": "memory_created", "id": identifier, "path": str(path.relative_to(self.vault)), "redactions": findings})
        return path

    def get_by_id(self, identifier: str) -> Path | None:
        for path in self.vault.rglob("*.md"):
            try:
                metadata, _ = read_note(path)
            except (OSError, ValueError):
                continue
            if metadata.get("id") == identifier or path.stem == identifier:
                return path
        return None

    def set_status(self, identifier: str, status: str) -> Path:
        if status not in VALID_STATUSES:
            raise ValueError(f"unsupported status: {status}")
        path = self.get_by_id(identifier)
        if not path:
            raise FileNotFoundError(f"note not found: {identifier}")
        metadata, body = read_note(path)
        metadata["status"] = status
        metadata["updated"] = _now()
        write_note(path, metadata, body)
        self.journal.append({"event": "status_changed", "id": str(metadata.get("id", path.stem)), "status": status})
        return path

    def supersede(self, identifier: str, kind: str, title: str, body: str, fields: dict[str, object] | None = None) -> Path:
        old = self.get_by_id(identifier)
        if not old:
            raise FileNotFoundError(f"note not found: {identifier}")
        self.set_status(str(read_note(old)[0].get("id", old.stem)), "superseded")
        from .relations import RelationStore
        new_path = self.create_memory(kind, title, body, dict(fields or {}))
        RelationStore(self.vault).add(new_path.stem, "supersedes", str(read_note(old)[0].get("id", old.stem)))
        return new_path
