from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re

from .config import VaultConfig
from .ids import new_id
from .journal import Journal
from .notes import write_note
from .privacy import redact_sensitive

RELATIONS = {"supports", "contradicts", "derived-from", "implements", "blocked-by", "supersedes", "part-of", "applies-to", "related-to"}


class RelationStore:
    def __init__(self, vault: Path):
        self.config = VaultConfig.load(Path(vault))
        self.vault = self.config.vault
        self.journal = Journal(self.vault / ".memory/journal/events.jsonl")

    def add(self, source: str, relation: str, target: str, evidence: str | None = None) -> Path:
        relation = relation.lower()
        if relation not in RELATIONS:
            raise ValueError(f"unsupported relation: {relation}")
        identifier = new_id("rel")
        path = self.vault / "relations" / f"{identifier}.md"
        metadata = {"memory_schema": 1, "id": identifier, "type": "relation", "title": f"{source} {relation} {target}",
                    "status": "active", "created": datetime.now(timezone.utc).isoformat(), "updated": datetime.now(timezone.utc).isoformat(),
                    "source": source, "relation": relation, "target": target}
        clean_evidence, _ = redact_sensitive(evidence or "", self.config.sensitive_patterns)
        body = f"# {relation}\n\n- Source: [[{source}]]\n- Target: [[{target}]]\n\n{clean_evidence}".rstrip()
        write_note(path, metadata, body)
        self.journal.append({"event": "relation_created", "id": identifier, "source": source, "target": target, "relation": relation})
        return path
