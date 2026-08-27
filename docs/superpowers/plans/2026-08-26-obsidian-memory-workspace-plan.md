# Obsidian Memory Workspace Implementation Plan

> **2026-08-28:** the disposable on-disk search index described in the original
> plan was never read by retrieval and has been removed. This document has
> been updated to match the shipped system.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Python CLI and Claude Code skill/plugin that manages linked Obsidian Markdown memories, entities, sessions, retrieval, and maintenance.

**Architecture:** A dependency-light Python package owns the canonical vault contract and workflows. The CLI exposes stable commands for initialization, saving, recall, sessions, entities, review, and diagnostics. Claude Code integration is a thin skill/plugin layer that invokes the CLI and documents memory behavior; Markdown remains authoritative.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `pathlib`, `yaml`-free frontmatter parser), JSONL journal, pytest, Markdown/YAML-compatible frontmatter, optional provider interfaces without required network dependencies.

## Global Constraints

- Obsidian Markdown and YAML frontmatter are the canonical data store.
- No network access is required for core operation.
- Optional embeddings and summarization are replaceable derived adapters.
- Stable IDs must not depend on filenames.
- Managed writes must be atomic and journaled.
- Secret filtering runs before persistence.
- Hooks fail open and must not block the primary coding workflow.
- Contradictory and stale notes are reported for review, not silently overwritten.
- Existing vault files are never deleted by initialization.

---

### Task 1: Project scaffold and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/obsidian_memory/__init__.py`
- Create: `src/obsidian_memory/cli.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`

**Interfaces:**
- Produces an installable package and `obsidian-memory` console entry point.
- `obsidian_memory.cli.main(argv: list[str] | None) -> int` is the CLI entry point.

- [ ] **Step 1: Write the failing test**

```python
def test_package_exposes_version():
    import obsidian_memory
    assert obsidian_memory.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -q`
Expected: FAIL because the package does not exist.

- [ ] **Step 3: Write minimal implementation**

Create the package with `__version__ = "0.1.0"`, a `main` function that returns `0`, and a `pyproject.toml` console script entry point.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_smoke.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src tests .gitignore
git commit -m "build: scaffold memory workspace package"
```

### Task 2: Vault configuration, schemas, IDs, and atomic notes

**Files:**
- Create: `src/obsidian_memory/config.py`
- Create: `src/obsidian_memory/notes.py`
- Create: `src/obsidian_memory/ids.py`
- Create: `tests/test_notes.py`

**Interfaces:**
- `VaultConfig.load(vault: Path) -> VaultConfig`
- `VaultConfig.initialize(vault: Path) -> VaultConfig`
- `write_note(path: Path, frontmatter: dict[str, object], body: str) -> None`
- `read_note(path: Path) -> tuple[dict[str, object], str]`
- `new_id(prefix: str) -> str`

- [ ] **Step 1: Write failing tests**

```python
def test_initialize_creates_default_layout(tmp_path):
    config = VaultConfig.initialize(tmp_path)
    assert (tmp_path / "memories/semantic").is_dir()
    assert (tmp_path / ".memory/config.json").is_file()
    assert config.schema_version == 1

def test_note_round_trip_uses_frontmatter(tmp_path):
    path = tmp_path / "note.md"
    write_note(path, {"id": "mem_test", "type": "semantic", "confidence": 0.8}, "A claim.")
    metadata, body = read_note(path)
    assert metadata["id"] == "mem_test"
    assert body == "A claim."

def test_initialize_does_not_replace_existing_file(tmp_path):
    welcome = tmp_path / "Welcome.md"
    welcome.write_text("keep", encoding="utf-8")
    VaultConfig.initialize(tmp_path)
    assert welcome.read_text(encoding="utf-8") == "keep"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_notes.py -q`
Expected: FAIL because configuration and note functions are undefined.

- [ ] **Step 3: Implement minimal configuration and notes**

Use JSON for `.memory/config.json` while emitting YAML-compatible frontmatter. Create the specified folders with `mkdir(exist_ok=True)`. Serialize scalar values, lists, and mappings deterministically; parse the same subset on read. Write a temporary sibling file, flush it, and replace the target atomically. Generate IDs using timestamp plus random suffix and never derive them from paths.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_notes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_memory tests/test_notes.py
git commit -m "feat: add vault configuration and note contract"
```

### Task 3: Privacy filtering and journaled persistence

**Files:**
- Create: `src/obsidian_memory/privacy.py`
- Create: `src/obsidian_memory/journal.py`
- Create: `tests/test_privacy.py`

**Interfaces:**
- `redact_sensitive(text: str, extra_patterns: list[str] | None = None) -> tuple[str, list[str]]`
- `is_ignored(text: str, markers: tuple[str, ...] = (...)) -> bool`
- `Journal.append(event: dict[str, object]) -> None`

- [ ] **Step 1: Write failing tests**

```python
def test_redacts_common_token():
    clean, findings = redact_sensitive("token=ghp_abcdefghijklmnopqrstuvwxyz123456")
    assert "ghp_" not in clean
    assert findings

def test_ignore_marker_blocks_capture():
    assert is_ignored("normal text\n<!-- memory:ignore -->\nsecret")

def test_journal_appends_jsonl(tmp_path):
    journal = Journal(tmp_path / ".memory/journal/events.jsonl")
    journal.append({"event": "saved", "id": "mem_1"})
    assert '"event": "saved"' in journal.path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_privacy.py -q`
Expected: FAIL because privacy and journal modules are missing.

- [ ] **Step 3: Implement filters and journal**

Detect common GitHub/OpenAI-style tokens, private-key blocks, bearer tokens, and configurable regex patterns. Replace secrets with `[REDACTED]` and return finding labels. Treat configured ignore markers as capture suppression. Ensure journal parent directories exist and append one JSON object per line with an ISO timestamp.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_privacy.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_memory tests/test_privacy.py
git commit -m "feat: add privacy filtering and memory journal"
```

### Task 4: Entities and typed memories

**Files:**
- Create: `src/obsidian_memory/store.py`
- Create: `src/obsidian_memory/memories.py`
- Create: `tests/test_memories.py`

**Interfaces:**
- `MemoryStore(vault: Path)`
- `MemoryStore.create_entity(kind: str, title: str, fields: dict[str, object]) -> Path`
- `MemoryStore.create_memory(kind: str, title: str, body: str, fields: dict[str, object]) -> Path`
- `MemoryStore.get_by_id(identifier: str) -> Path | None`

- [ ] **Step 1: Write failing tests**

```python
def test_create_project_and_semantic_memory_links_entity(tmp_path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    project = store.create_entity("project", "Memory Workspace", {})
    memory = store.create_memory("semantic", "Canonical store", "Markdown is canonical.", {"entities": [project.stem]})
    metadata, body = read_note(memory)
    assert metadata["type"] == "semantic"
    assert project.stem in metadata["entities"]
    assert body.startswith("Markdown")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memories.py -q`
Expected: FAIL because `MemoryStore` is missing.

- [ ] **Step 3: Implement store and memory factory**

Map entity kinds to `entities/users`, `entities/projects`, and `entities/agents`; map memory kinds to their required directories. Add stable IDs, timestamps, status, confidence, importance, tags, and links. Redact body text before writing, reject ignored content, and journal successful writes. Support aliases and lookup by ID or filename stem.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_memories.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_memory tests/test_memories.py
git commit -m "feat: add entities and typed memory persistence"
```

### Task 5: Sessions and complete session overviews

**Files:**
- Create: `src/obsidian_memory/sessions.py`
- Create: `tests/test_sessions.py`

**Interfaces:**
- `SessionStore.start(project: str | None, user: str | None, agent: str | None) -> Path`
- `SessionStore.finalize(session: str, overview: dict[str, object]) -> Path`
- `SessionStore.load_context(project: str | None, limit: int = 10) -> list[dict[str, object]]`

- [ ] **Step 1: Write failing tests**

```python
def test_finalize_session_contains_required_sections(tmp_path):
    VaultConfig.initialize(tmp_path)
    sessions = SessionStore(tmp_path)
    path = sessions.start("project_1", "user_1", "agent_1")
    sessions.finalize(path.stem, {"goals": ["ship"], "decisions": ["use Markdown"], "work": ["implemented"], "discoveries": [], "unresolved": ["provider choice"], "follow_ups": []})
    _, body = read_note(path)
    for heading in ("## Goals", "## Decisions", "## Work", "## Discoveries", "## Unresolved Questions", "## Follow-ups"):
        assert heading in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sessions.py -q`
Expected: FAIL because session storage is missing.

- [ ] **Step 3: Implement session lifecycle**

Create session notes with entity links and required headings. Finalization updates metadata, writes all overview sections, and journals the event. Context loading reads recent session notes for the selected project and returns source metadata without failing on malformed notes.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_sessions.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_memory tests/test_sessions.py
git commit -m "feat: add session lifecycle and overviews"
```

### Task 6: Relations and offline hybrid retrieval

**Files:**
- Create: `src/obsidian_memory/relations.py`
- Create: `src/obsidian_memory/retrieval.py`
- Create: `tests/test_retrieval.py`

**Interfaces:**
- `RelationStore.add(source: str, relation: str, target: str, evidence: str | None = None) -> Path`
- `Retriever.search(query: str, filters: dict[str, object] | None = None, limit: int = 10) -> list[dict[str, object]]`

- [ ] **Step 1: Write failing tests**

```python
def test_recall_matches_text_and_expands_related_notes(tmp_path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    first = store.create_memory("semantic", "Atomic writes", "Use atomic Markdown writes.", {})
    second = store.create_memory("procedural", "Write workflow", "Write a temporary file then replace it.", {})
    RelationStore(tmp_path).add(first.stem, "implements", second.stem)
    results = Retriever(tmp_path).search("atomic Markdown", limit=5)
    ids = {item["id"] for item in results}
    assert first.stem in ids
    assert second.stem in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_retrieval.py -q`
Expected: FAIL because relation and retrieval modules are missing.

- [ ] **Step 3: Implement relation storage and retrieval**

Store typed relation notes with source/target IDs and evidence. Search managed Markdown notes using case-insensitive token matching, metadata filters, recency, importance, confidence, and relation expansion. Return IDs, title, type, excerpt, confidence, score, and source path. Ignore malformed notes and never require embeddings. Define a provider protocol for future derived semantic search but do not add a network dependency.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_retrieval.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_memory tests/test_retrieval.py
git commit -m "feat: add typed relations and offline retrieval"
```

### Task 7: Review and doctor diagnostics

**Files:**
- Create: `src/obsidian_memory/maintenance.py`
- Create: `tests/test_maintenance.py`

**Interfaces:**
- `review(vault: Path) -> dict[str, list[dict[str, object]]]`
- `doctor(vault: Path) -> dict[str, list[str]]`

- [ ] **Step 1: Write failing tests**

```python
def test_doctor_reports_broken_relation_target(tmp_path):
    VaultConfig.initialize(tmp_path)
    RelationStore(tmp_path).add("missing_source", "supports", "missing_target")
    report = doctor(tmp_path)
    assert report["broken_links"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_maintenance.py -q`
Expected: FAIL because maintenance functions are missing.

- [ ] **Step 3: Implement maintenance**

`doctor` reports malformed frontmatter, duplicate IDs, missing relation endpoints, orphaned managed notes, invalid statuses, and contradictions where both notes explicitly conflict. `review` groups candidates, stale items, contradictions, and probable duplicates. Never modify canonical notes during diagnostics.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_maintenance.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_memory tests/test_maintenance.py
git commit -m "feat: add review and doctor diagnostics"
```

### Task 8: CLI commands and Claude Code integration

**Files:**
- Modify: `src/obsidian_memory/cli.py`
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/commands/memory.md`
- Create: `.claude-plugin/hooks/session-start.sh`
- Create: `.claude-plugin/hooks/session-end.sh`
- Create: `skills/memory/SKILL.md`
- Create: `skills/memory/references/schemas.md`
- Create: `skills/memory/references/privacy.md`
- Create: `README.md`
- Create: `tests/test_cli.py`

**Interfaces:**
- CLI subcommands: `init`, `save`, `recall`, `session`, `entity`, `review`, `doctor`.
- Hooks invoke `obsidian-memory` only when configured and return success even when memory operations fail.

- [ ] **Step 1: Write failing tests**

```python
def test_cli_init_and_recall(tmp_path, capsys):
    assert main(["init", "--vault", str(tmp_path)]) == 0
    assert main(["save", "--vault", str(tmp_path), "--type", "semantic", "--title", "Local", "--body", "Works offline"]) == 0
    assert main(["recall", "--vault", str(tmp_path), "offline"]) == 0
    assert "Works offline" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL because CLI subcommands are not implemented.

- [ ] **Step 3: Implement CLI and integration files**

Use `argparse` with explicit `--vault` support and JSON output option. Map each command to the package interfaces and return nonzero only for user input or validation errors. The plugin manifest and command documentation describe installation and vault configuration. The skill defines capture/retrieval/session/entity/review/privacy behavior and links to schemas. Hooks read `OBSIDIAN_MEMORY_VAULT`, call the CLI defensively, redirect failures to a log, and exit `0`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src .claude-plugin skills README.md tests
git commit -m "feat: expose memory CLI and Claude Code skill"
```

### Task 9: End-to-end verification and packaging checks

**Files:**
- Modify: `README.md`
- Create: `tests/test_end_to_end.py`

- [ ] **Step 1: Write end-to-end failing test**

Exercise initialization, entity creation, session finalization, typed memory creation, relation creation, recall, and doctor in one temporary vault.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_end_to_end.py -q`
Expected: FAIL until all integration boundaries are wired.

- [ ] **Step 3: Implement only integration fixes**

Correct command wiring, path handling, schema consistency, and documentation examples revealed by the test. Do not expand the feature set in this task.

- [ ] **Step 4: Run complete verification**

Run:

```bash
python -m pytest -q
python -m compileall -q src
python -m obsidian_memory.cli --help
```

Expected: all tests pass, compilation succeeds, and help lists every required command.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_end_to_end.py src
 git commit -m "test: verify memory workspace end to end"
```

## Coverage Check

- Vault layout, schemas, IDs, and atomic writes: Task 2.
- Privacy and journaling: Task 3.
- Entities and all typed memories: Task 4.
- Session overview and lifecycle: Task 5.
- Relations and offline retrieval: Task 6.
- Review and diagnostics: Task 7.
- Plugin, skill, hooks, and CLI: Task 8.
- End-to-end acceptance: Task 9.
- Optional embedding/summarization providers: Task 6 provider protocol; no provider implementation is required for v1.

## Self-review

- No unresolved placeholders or TODOs are present.
- Interfaces use consistent `Path`, `dict`, and result shapes across tasks.
- Canonical files remain Markdown; JSON is used only for configuration and the journal.
- Existing Obsidian files are preserved by initialization.
- The implementation is intentionally dependency-light so offline behavior is testable and reliable.
