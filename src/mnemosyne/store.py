from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re

from .config import VaultConfig
from .ids import new_id
from .journal import Journal, current_session_id
from .memories import MEMORY_TYPES as ALL_MEMORY_TYPES, RECORD_TYPES
from .notes import read_note, write_note
from .privacy import is_ignored, redact_sensitive

ENTITY_DIRS = {"user": "users", "person": "users", "project": "projects", "agent": "agents"}
MEMORY_TYPES = set(ALL_MEMORY_TYPES) - RECORD_TYPES
VALID_STATUSES = {"candidate", "active", "superseded", "archived", "rejected"}


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _link(identifier: str) -> str:
    return identifier if identifier.startswith("[[") else f"[[{identifier}]]"


class MemoryStore:
    LINK_FIELDS = {"entities", "source_sessions", "related"}

    def __init__(self, vault: Path):
        self.config = VaultConfig.load(Path(vault))
        self.vault = self.config.vault
        self.journal = Journal(self.vault / ".memory/journal/events.jsonl")

    def _normalize_links(self, fields: dict[str, object]) -> dict[str, object]:
        out = dict(fields)
        for field in self.LINK_FIELDS:
            values = out.get(field)
            if values is None:
                continue
            if isinstance(values, str):
                values = [values]
            if isinstance(values, list):
                out[field] = [v if isinstance(v, str) and v.startswith('[[') else f'[[{v}]]' for v in values]
        return out

    def create_entity(self, kind: str, title: str, fields: dict[str, object]) -> Path:
        fields = dict(fields)
        folder = ENTITY_DIRS.get(kind.lower())
        if not folder:
            raise ValueError(f"unsupported entity kind: {kind}")
        title, title_findings = redact_sensitive(title, self.config.sensitive_patterns)
        identifier = new_id(kind)
        path = self.vault / "entities" / folder / f"{slugify(title)}-{identifier}.md"
        description = fields.pop("description", "")
        description, findings = redact_sensitive(str(description), self.config.sensitive_patterns)
        findings = sorted(set(findings + title_findings))
        if is_ignored(description, tuple(self.config.ignore_markers)):
            raise ValueError("entity capture is excluded")
        metadata = {"memory_schema": 1, "id": identifier, "type": kind.lower(), "title": title,
                    "status": fields.pop("status", "active"), "created": _now(), "updated": _now(), **fields}
        active = current_session_id(self.vault)
        if active and "source_sessions" not in metadata:
            metadata["source_sessions"] = [active]
        if findings:
            metadata["redactions"] = findings
        metadata = self._normalize_links(metadata)
        write_note(path, metadata, f"# {title}\n\n{description}".rstrip())
        self.journal.append({"event": "entity_created", "id": identifier, "path": str(path.relative_to(self.vault))})
        return path

    def create_memory(self, kind: str, title: str, body: str, fields: dict[str, object]) -> Path:
        fields = dict(fields)
        active = current_session_id(self.vault)
        if active and "source_sessions" not in fields:
            fields["source_sessions"] = [active]
        kind = kind.lower()
        if kind not in MEMORY_TYPES:
            raise ValueError(f"unsupported memory type: {kind}")
        if self.config.is_path_excluded(self.vault / "memories" / kind) or is_ignored(body, tuple(self.config.ignore_markers)):
            raise ValueError("memory capture is excluded")
        clean, findings = redact_sensitive(body, self.config.sensitive_patterns)
        title, _ = redact_sensitive(title, self.config.sensitive_patterns)
        identifier = new_id("mem")
        path = self.vault / "memories" / kind / f"{slugify(title)}-{identifier}.md"
        metadata = {"memory_schema": 1, "id": identifier, "type": kind, "title": title,
                    "status": fields.pop("status", "candidate"), "created": _now(), "updated": _now(),
                    "confidence": fields.pop("confidence", 0.5), "importance": fields.pop("importance", 0.5),
                    "tags": fields.pop("tags", [f"memory/{kind}"]), **self._normalize_links(fields)}
        write_note(path, metadata, clean)
        self.journal.append({"event": "memory_created", "id": identifier, "path": str(path.relative_to(self.vault)), "redactions": findings})
        return path

    def get_by_id(self, identifier: str) -> Path | None:
        paths = list(self.vault.rglob("*.md"))
        for path in paths:
            if path.stem == identifier:
                return path
        for path in paths:
            try:
                metadata, _ = read_note(path)
            except (OSError, ValueError):
                continue
            if metadata.get("id") == identifier:
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

    def update_memory(self, identifier: str, body: str | None = None, title: str | None = None,
                      confidence: float | None = None, importance: float | None = None) -> Path:
        """Amend a memory in place (no new note), updating the timestamp."""
        path = self.get_by_id(identifier)
        if not path:
            raise FileNotFoundError(f"note not found: {identifier}")
        metadata, current_body = read_note(path)
        if body is not None:
            clean, findings = redact_sensitive(body, self.config.sensitive_patterns)
            if is_ignored(clean, tuple(self.config.ignore_markers)):
                raise ValueError("memory update is excluded")
            current_body = clean
            metadata["redactions"] = findings
        if title is not None:
            metadata["title"] = title
        if confidence is not None:
            metadata["confidence"] = confidence
        if importance is not None:
            metadata["importance"] = importance
        metadata["updated"] = _now()
        write_note(path, metadata, current_body)
        self.journal.append({"event": "memory_updated", "id": str(metadata.get("id", path.stem))})
        return path

    def create_question(self, question: str, answer: str, correct: bool,
                        topic: str | None = None, difficulty: str | None = None,
                        fields: dict[str, object] | None = None) -> Path:
        """Record a question (quiz/probe/learning) with its answer and correctness."""
        if not question.strip() or not answer.strip():
            raise ValueError("question and answer are required")
        clean_q, _ = redact_sensitive(question, self.config.sensitive_patterns)
        clean_a, _ = redact_sensitive(answer, self.config.sensitive_patterns)
        if is_ignored(clean_q + clean_a, tuple(self.config.ignore_markers)):
            raise ValueError("question capture is excluded")
        identifier = new_id("question")
        path = self.vault / "memories" / "questions" / f"{slugify(clean_q[:60])}-{identifier}.md"
        record_fields = dict(fields or {})
        active = current_session_id(self.vault)
        if active and "source_sessions" not in record_fields:
            record_fields["source_sessions"] = [active]
        metadata = {"memory_schema": 1, "id": identifier, "type": "question", "title": clean_q[:80],
                    "status": "active", "created": _now(), "updated": _now(),
                    "question": clean_q, "answer": clean_a, "correct": bool(correct),
                    "topic": topic, "difficulty": difficulty, **self._normalize_links(record_fields)}
        write_note(path, metadata, f"**Q:** {clean_q}\n\n**A:** {clean_a}\n\n*Correct: {bool(correct)}*")
        self.journal.append({"event": "question_recorded", "id": identifier, "correct": bool(correct)})
        return path

    def create_decision(self, decision: str, context: str = "", options: list[str] | None = None,
                        chosen: str | None = None, rationale: str = "",
                        fields: dict[str, object] | None = None) -> Path:
        """Record a decision with its context, options, choice, and rationale."""
        if not decision.strip() or not rationale.strip():
            raise ValueError("decision and rationale are required")
        clean_d, _ = redact_sensitive(decision, self.config.sensitive_patterns)
        clean_c, _ = redact_sensitive(context, self.config.sensitive_patterns)
        clean_r, _ = redact_sensitive(rationale, self.config.sensitive_patterns)
        if is_ignored(clean_d + clean_c + clean_r, tuple(self.config.ignore_markers)):
            raise ValueError("decision capture is excluded")
        identifier = new_id("decision")
        path = self.vault / "memories" / "decisions" / f"{slugify(clean_d[:60])}-{identifier}.md"
        record_fields = dict(fields or {})
        active = current_session_id(self.vault)
        if active and "source_sessions" not in record_fields:
            record_fields["source_sessions"] = [active]
        metadata = {"memory_schema": 1, "id": identifier, "type": "decision", "title": clean_d[:80],
                    "status": "active", "created": _now(), "updated": _now(),
                    "decision": clean_d, "context": clean_c, "options": list(options or []),
                    "chosen": chosen, "rationale": clean_r, **self._normalize_links(record_fields)}
        body = f"# {clean_d}\n\n**Context:** {clean_c}\n\n**Options:** {', '.join(str(o) for o in (options or [])) or 'n/a'}\n\n**Chosen:** {chosen or 'n/a'}\n\n**Rationale:** {clean_r}"
        write_note(path, metadata, body)
        self.journal.append({"event": "decision_recorded", "id": identifier, "chosen": chosen})
        return path

    def create_quiz(self, topic: str, score: int, total: int, weak_areas: list[str] | None = None,
                    question_ids: list[str] | None = None, fields: dict[str, object] | None = None) -> Path:
        """Record a graded quiz batch: score, topic, weak areas, and linked questions."""
        if total <= 0:
            raise ValueError("quiz total must be a positive integer")
        clean_topic, _ = redact_sensitive(topic, self.config.sensitive_patterns)
        if is_ignored(clean_topic, tuple(self.config.ignore_markers)):
            raise ValueError("quiz capture is excluded")
        identifier = new_id("quiz")
        path = self.vault / "memories" / "quizzes" / f"{slugify(clean_topic[:60])}-{identifier}.md"
        record_fields = dict(fields or {})
        active = current_session_id(self.vault)
        if active and "source_sessions" not in record_fields:
            record_fields["source_sessions"] = [active]
        links = [f"[[{q}]]" for q in (question_ids or [])]
        metadata = {"memory_schema": 1, "id": identifier, "type": "quiz", "title": clean_topic[:80],
                    "status": "active", "created": _now(), "updated": _now(),
                    "topic": clean_topic, "score": int(score), "total": int(total),
                    "weak_areas": list(weak_areas or []), "questions": links,
                    **self._normalize_links(record_fields)}
        lines = [f"# Quiz: {clean_topic}", "", f"**Score:** {score}/{total} ({round(100 * score / total)}%)", ""]
        if weak_areas:
            lines += ["## Weak areas", ""] + [f"- {area}" for area in weak_areas] + [""]
        if links:
            lines += ["## Questions", ""] + [f"- {link}" for link in links] + [""]
        write_note(path, metadata, "\n".join(lines).rstrip())
        self.journal.append({"event": "quiz_recorded", "id": identifier, "score": int(score), "total": int(total)})
        return path

    def supersede(self, identifier: str, kind: str, title: str, body: str, fields: dict[str, object] | None = None) -> Path:
        old = self.get_by_id(identifier)
        if not old:
            raise FileNotFoundError(f"note not found: {identifier}")
        self.set_status(old.stem, "superseded")
        from .relations import RelationStore
        new_path = self.create_memory(kind, title, body, dict(fields or {}))
        RelationStore(self.vault).add(new_path.stem, "supersedes", old.stem)
        return new_path
