---
name: memory
description: Capture, retrieve, relate, review, and maintain durable local memory in an Obsidian vault.
---

# Obsidian Memory

Use this skill whenever durable user, project, agent, session, or workflow context should be recalled or saved.

## Subskills

1. **Capture:** classify one concise claim as semantic, episodic, procedural, prospective, parametric, or retrieval memory. Keep source-session links and confidence.
2. **Retrieval:** query exact text and metadata first; use graph neighbors next. Return bounded context with type, confidence, reason, and source path.
3. **Session overview:** preserve request, loaded context, goals, decisions, work, discoveries, unresolved questions, follow-ups, extracted memories, and related sessions.
4. **Entities:** maintain explicit user, project, and agent profiles. Confirm uncertain personal/high-impact claims.
5. **Relations:** use only `supports`, `contradicts`, `derived-from`, `implements`, `blocked-by`, `supersedes`, `part-of`, `applies-to`, and `related-to`.
6. **Review:** surface candidates, stale notes, duplicates, contradictions, broken links, and orphans. Never silently overwrite contradictory facts.
7. **Privacy:** apply [references/privacy.md](references/privacy.md) before any capture.
8. **Maintenance:** rebuild disposable indexes and run doctor without changing canonical notes.

## Workflow

1. Resolve vault from `--vault`, then `OBSIDIAN_MEMORY_VAULT`; the documented local example is `C:/Memory`.
2. At session start run `obsidian-memory session --vault <vault> context` and retrieve relevant open prospective items and recent sessions.
3. During work use `save`, `entity`, and `recall` explicitly.
4. At session end start or finalize a session using a complete JSON overview.
5. Run `review` for promotion decisions and `doctor` for structural issues.

Read [references/schemas.md](references/schemas.md) for the canonical contract. Markdown/YAML notes are authoritative. JSON configuration, journals, and indexes are operational or derived artifacts only.
