from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from .config import VaultConfig
from .notes import read_note

MANAGED_ROOTS = ("entities", "sessions", "memories", "relations")
VALID_STATUSES = {"candidate", "active", "complete", "superseded", "archived", "rejected"}
MEMORY_TYPES = {"semantic", "procedural", "prospective", "parametric", "episodic", "retrieval", "question", "decision", "quiz"}


def _notes(vault: Path):
    for root_name in MANAGED_ROOTS:
        root = vault / root_name
        if root.exists():
            yield from root.rglob("*.md")


def doctor(vault: Path) -> dict[str, list[str]]:
    vault = Path(vault).resolve()
    VaultConfig.load(vault)
    report = {key: [] for key in ("malformed", "duplicate_ids", "broken_links", "orphans", "invalid_statuses", "contradictions", "stale")}
    records = []
    ids: dict[str, Path] = {}
    for path in _notes(vault):
        try:
            metadata, body = read_note(path)
        except (OSError, ValueError) as exc:
            report["malformed"].append(f"{path.relative_to(vault)}: {exc}")
            continue
        identifier = metadata.get("id")
        if identifier in ids:
            report["duplicate_ids"].append(str(identifier))
        elif identifier:
            ids[str(identifier)] = path
        status = metadata.get("status")
        if status not in VALID_STATUSES:
            report["invalid_statuses"].append(str(path.relative_to(vault)))
        records.append((path, metadata, body))
    for path, metadata, _ in records:
        if metadata.get("type") == "relation":
            for field in ("source", "target"):
                value = metadata.get(field)
                if value and str(value) not in ids and not any(p.stem == str(value) for p in _notes(vault)):
                    report["broken_links"].append(f"{path.relative_to(vault)} -> {value}")
        for field in ("source_sessions", "entities", "related"):
            values = metadata.get(field, [])
            if isinstance(values, str): values = [values]
            for value in values if isinstance(values, list) else []:
                target = str(value).strip("[]")
                if target and not any(p.stem == target or str(m.get("id")) == target for p, m, _ in records):
                    report["broken_links"].append(f"{path.relative_to(vault)} -> {target}")
    for path, metadata, body in records:
        if metadata.get("type") in MEMORY_TYPES and not metadata.get("source_sessions") and "/memories/" in str(path).replace("\\", "/"):
            report["orphans"].append(str(path.relative_to(vault)))
        if metadata.get("type") == "semantic" and "contradicts:" in body.lower():
            report["contradictions"].append(str(path.relative_to(vault)))
        updated = metadata.get("updated", "")
        if isinstance(updated, str) and updated[:10]:
            try:
                if (datetime.now(timezone.utc) - datetime.fromisoformat(updated)).days > 180:
                    report["stale"].append(str(path.relative_to(vault)))
            except ValueError:
                pass
    return report


def review(vault: Path) -> dict[str, list[dict[str, object]]]:
    groups = {key: [] for key in ("candidates", "stale", "contradictions", "duplicates")}
    report = doctor(vault)
    for path in _notes(Path(vault)):
        try:
            metadata, _ = read_note(path)
        except (OSError, ValueError):
            continue
        item = {"id": metadata.get("id"), "title": metadata.get("title", path.stem), "path": str(path)}
        if metadata.get("status") == "candidate": groups["candidates"].append(item)
    groups["stale"] = [{"path": item} for item in report["stale"]]
    groups["contradictions"] = [{"path": item} for item in report["contradictions"]]
    groups["duplicates"] = [{"id": item} for item in report["duplicate_ids"]]
    return groups


def _read_entry(path: Path, vault: Path) -> dict[str, object] | None:
    try:
        metadata, body = read_note(path)
    except (OSError, ValueError):
        return None
    return {"id": metadata.get("id", path.stem), "title": metadata.get("title", path.stem),
            "type": metadata.get("type"), "path": str(path.relative_to(vault)), "excerpt": body[:500]}


def rebuild_index(vault: Path) -> Path:
    vault = Path(vault).resolve()
    config = VaultConfig.load(vault)
    target = vault / ".memory/index/notes.json"
    state_path = target.with_name(".state.json")
    entries = []
    for path in _notes(vault):
        entry = _read_entry(path, vault)
        if entry is not None:
            entries.append(entry)
    _write_index(target, state_path, entries, vault)
    return target


def update_index(vault: Path) -> Path:
    """Incrementally refresh the search index, skipping notes whose mtime is unchanged."""
    vault = Path(vault).resolve()
    config = VaultConfig.load(vault)
    target = vault / ".memory/index/notes.json"
    state_path = target.with_name(".state.json")
    existing: dict[str, dict[str, object]] = {}
    if target.exists():
        try:
            existing = {e["path"]: e for e in json.loads(target.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, OSError):
            existing = {}
    state: dict[str, int] = {}
    if state_path.exists():
        try:
            state = {k: int(v) for k, v in json.loads(state_path.read_text(encoding="utf-8")).items()}
        except (json.JSONDecodeError, OSError):
            state = {}
    entries: list[dict[str, object]] = []
    for path in _notes(vault):
        rel = str(path.relative_to(vault))
        try:
            mtime = int(path.stat().st_mtime_ns)
        except OSError:
            continue
        if rel in existing and state.get(rel) == mtime:
            entries.append(existing[rel])
        else:
            entry = _read_entry(path, vault)
            if entry is not None:
                entries.append(entry)
                state[rel] = mtime
    _write_index(target, state_path, entries, vault)
    return target


def _write_index(target: Path, state_path: Path, entries: list[dict[str, object]], vault: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(entries, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(target)
    state: dict[str, int] = {}
    for entry in entries:
        rel = str(entry["path"])
        note = vault / rel
        try:
            state[rel] = int(note.stat().st_mtime_ns)
        except OSError:
            continue
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
