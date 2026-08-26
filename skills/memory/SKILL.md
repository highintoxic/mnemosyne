---
name: memory
description: Capture, retrieve, relate, review, and maintain durable local memory in an Obsidian vault. Use whenever durable user, project, agent, session, or workflow context should be recalled or saved. Available as MCP tools (obsidian-memory-mcp) or CLI (obsidian-memory).
---

# Obsidian Memory

Use this skill whenever durable user, project, agent, session, or workflow context should be recalled or saved. The vault is `C:/Memory` (override with `OBSIDIAN_MEMORY_VAULT`).

## Access

The memory workspace is exposed two ways; prefer MCP tools when available:

- **MCP tools** (registered as `obsidian-memory` in Claude Code): `init`, `save`, `recall`, `entity`, `session_start`, `session_finalize`, `session_context`, `promote`, `reject`, `supersede`, `review`, `index`, `doctor`.
- **CLI**: `obsidian-memory <command> --vault <vault>` (defaults to `OBSIDIAN_MEMORY_VAULT` or `C:/Memory`).

## Subskills

1. **Capture:** classify one concise claim as semantic, episodic, procedural, prospective, parametric, or retrieval memory. Keep source-session links and confidence.
2. **Retrieval:** query exact text and metadata first; use graph neighbors next. Return bounded context with type, confidence, reason, and source path.
3. **Session overview:** preserve request, loaded context, goals, decisions, work, discoveries, unresolved questions, follow-ups, extracted memories, and related sessions.
4. **Entities:** maintain explicit user, project, and agent profiles. Confirm uncertain personal/high-impact claims.
5. **Relations:** use only `supports`, `contradicts`, `derived-from`, `implements`, `blocked-by`, `supersedes`, `part-of`, `applies-to`, and `related-to`. Never create self-relations.
6. **Review:** surface candidates, stale notes, duplicates, contradictions, broken links, and orphans. Never silently overwrite contradictory facts.
7. **Privacy:** apply [references/privacy.md](references/privacy.md) before any capture.
8. **Maintenance:** rebuild disposable indexes and run doctor without changing canonical notes.

## Workflow

1. **Session start** — call `session_start` (or `obsidian-memory session start`) with the active project/user/agent, then `recall` for relevant context:
   ```
   recall("", limit=0)         # no-op
   recall(query="project conventions", limit=10)
   session_context(project=..., limit=10)
   ```
   Inject retrieved context into the conversation, each item labeled with type + confidence + source path.
2. **During work** — whenever durable facts, decisions, workflows, events, preferences, or future actions emerge, `save` a typed memory:
   - `semantic` — durable facts/conclusions
   - `episodic` — what happened (experiments, failures, decisions)
   - `procedural` — repeatable workflows/instructions
   - `prospective` — future actions/reminders/deadlines
   - `parametric` — user preferences, project conventions, agent capabilities
   - `retrieval` — saved queries and context-assembly hints
   Link it: pass `entities`, `source_sessions`, `related` IDs so the Obsidian graph connects.
   Saves auto-link to the active session (the UserPromptSubmit hook also logs each prompt to the session's Activity Log).
   When a memory changes, call `update` with `id` + the fields to amend (`body`, `title`, `confidence`) instead of creating a duplicate.
3. **Session end** — call `session_finalize` with `auto=true` (builds the overview from the journal) plus explicit `decisions`; or pass a full JSON `overview`. This writes the complete session note (goals, work, discoveries, unresolved, follow-ups, extracted memories, activity log).
4. **Lifecycle** — `promote`/`reject` reviewed candidates; `supersede` outdated notes (marks old superseded + links `supersedes` relation).
5. **Maintenance** — `review` for promotion decisions, `doctor` for structural issues, `index` to rebuild the disposable search index.

## Retrieval behavior

`recall` returns bounded, source-linked results. Exact + metadata matching always works offline; set `semantic=true` to blend TF-IDF ranking; related notes come along via typed relations. Each result carries `id`, `title`, `type`, `confidence`, `score`, and `source_path` so you can cite where the memory came from.

## Privacy

Read [references/privacy.md](references/privacy.md) before any capture. Secrets are auto-redacted before persistence; `<!-- memory:ignore -->` markers block capture; personal/high-impact claims require confirmation when confidence is uncertain.

Read [references/schemas.md](references/schemas.md) for the canonical contract. Markdown/YAML notes are authoritative. JSON configuration, journals, and indexes are operational or derived artifacts only.
