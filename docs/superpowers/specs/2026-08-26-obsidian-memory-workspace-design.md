# Obsidian Memory Workspace — Design Specification

> **2026-08-28:** the disposable on-disk search index described in the original
> design was never read by retrieval and has been removed. This document has
> been updated to match the shipped system.

**Date:** 2026-08-26  
**Status:** Approved for specification review  
**Target:** Claude Code plugin + portable memory skill backed by an Obsidian vault

## 1. Summary

Build a local-first memory workspace that lets Claude Code and other compatible agents capture, organize, retrieve, and maintain durable context in an Obsidian vault. Obsidian Markdown and YAML frontmatter are the canonical data store. The Claude Code plugin supplies commands and lifecycle hooks; a portable skill supplies the taxonomy, schemas, linking rules, privacy rules, and retrieval behavior.

The system supports projects, users, agents, complete session overviews, typed memories, explicit relations, hybrid retrieval, and review workflows. Optional embedding or summarization providers may improve results but are never required for basic operation.

“Parametric memory” means explicit configuration and model knowledge—such as project conventions, agent capabilities, tool limits, and response preferences. It does not imply modifying model weights.

## 2. Goals and non-goals

### Goals

- Initialize a fresh Obsidian vault with a predictable, portable structure.
- Represent users, projects, agents, sessions, memories, and relations as readable linked notes.
- Capture a whole-session overview containing context, decisions, work, discoveries, unresolved questions, and follow-up items.
- Support semantic, episodic, procedural, prospective, parametric, and retrieval-oriented memory workflows.
- Retrieve bounded, source-linked context using exact search, metadata, recency, confidence, graph relationships, and optional embeddings.
- Preserve an auditable path from injected context to source notes and from session output to extracted memories.
- Operate offline by default and protect secrets and sensitive information.

### Non-goals for v1

- A required Obsidian community UI plugin.
- A remote database as the source of truth.
- Synchronization with third-party memory services.
- Editing Claude’s internal model parameters or weights.
- Silent autonomous promotion of uncertain personal facts.

## 3. Architecture

```text
Claude Code plugin
  ├── slash commands and configuration
  ├── session-start/session-end hooks
  ├── capture, recall, summaries, and entity management
  ├── validation, redaction, review, and maintenance
  └── optional local/remote semantic provider adapters
             │
             ▼
Portable memory skill
  ├── memory taxonomy and classification rules
  ├── versioned note schemas and templates
  ├── relation and linking conventions
  ├── retrieval and context-budget rules
  └── privacy and lifecycle policies
             │
             ▼
Obsidian vault (canonical Markdown + YAML)
  ├── entities: users, projects, agents
  ├── sessions and session overviews
  ├── typed memories
  ├── explicit relations
  └── generated reports
```

The plugin and skill must share a versioned schema contract. All writes should be atomic where practical, use a journal or backup strategy, and avoid modifying unrelated vault files.

## 4. Vault layout

```text
<configured-vault>/
├── entities/
│   ├── users/
│   ├── projects/
│   └── agents/
├── sessions/
├── memories/
│   ├── semantic/
│   ├── episodic/
│   ├── procedural/
│   ├── prospective/
│   ├── parametric/
│   └── retrieval/
├── relations/
├── reviews/              # doctor and human-review reports
├── templates/
└── .memory/
    ├── config.yaml
    └── journal/
```

The exact folder names are configurable only through a versioned configuration file; default conventions should remain stable so the vault stays portable.

## 5. Canonical note contract

Every managed note has a stable identifier and YAML frontmatter similar to:

```yaml
memory_schema: 1
id: mem_01J...
type: semantic
title: Short human-readable title
status: candidate # candidate | active | superseded | archived | rejected
created: 2026-08-26T12:00:00Z
updated: 2026-08-26T12:00:00Z
confidence: 0.82
importance: 0.70
source_sessions:
  - "[[sessions/2026-08-26-project-session]]"
entities:
  - "[[entities/projects/obsidian-memory]]"
related:
  - "[[memories/procedural/test-workflow]]"
tags:
  - memory/semantic
```

The body contains a concise claim or record, evidence/source context, applicability, caveats, and links. IDs must not depend on filenames because notes may be renamed in Obsidian.

### Memory types

- **Semantic:** durable facts, concepts, definitions, project/domain knowledge, and explicit conclusions.
- **Episodic:** what happened in a particular session, event, experiment, failure, or decision.
- **Procedural:** repeatable instructions, workflows, recipes, and successful action sequences.
- **Prospective:** intended future actions, reminders, deadlines, triggers, and waiting conditions.
- **Parametric:** declared preferences, project conventions, agent capabilities, model/tool configuration, and operating constraints.
- **Retrieval:** saved queries, aliases, retrieval hints, related-note bundles, and context-assembly instructions. This is an optimization layer, not a replacement for source memories.

### Entities

User, project, and agent notes use the same stable-ID pattern and include aliases, description, status, ownership, relevant preferences/capabilities, and linked sessions/memories. A project may contain active goals and conventions. A user profile may contain explicitly approved preferences. An agent profile may contain capabilities, limitations, and tool conventions.

### Sessions

Each session note includes:

- session ID, timestamps, project/user/agent links, and source metadata;
- initial request and goals;
- context loaded at start, with source links;
- chronological or phase-based work summary;
- decisions and their rationale;
- files, commands, tools, and outputs relevant to the work;
- discoveries, assumptions, caveats, and unresolved questions;
- extracted candidate memories and explicit relations;
- prospective follow-up items and status;
- final summary and links to related sessions.

A session overview must remain useful when read without the original transcript.

### Relations

Relations may be inline links or dedicated relation notes for higher-value edges. Supported relation labels include `supports`, `contradicts`, `derived-from`, `implements`, `blocked-by`, `supersedes`, `part-of`, `applies-to`, and `related-to`. Contradictory claims are retained and surfaced for review rather than silently overwritten.

## 6. Lifecycle and workflows

### Initialization

`memory:init` validates the configured path, creates missing folders/templates/configuration, writes a schema version, and never deletes existing user content. It should offer a dry-run and report conflicts.

### Session start

The hook loads the active user, project, and agent; open prospective items; recent session summaries; and relevant memories. Context is ranked, deduplicated, capped by a token budget, and presented with note links, memory types, confidence, and retrieval reasons.

### Capture

Explicit commands and session-end extraction create candidate notes. Before writing, the system redacts likely credentials, API keys, tokens, private keys, and configured sensitive patterns. Ignore markers and per-folder policies can suppress capture. Uncertain personal facts require confirmation before promotion.

### Promotion and maintenance

Candidates are validated, normalized, deduplicated, and either promoted to `active`, left `candidate`, rejected, or linked as a revision. New information may supersede old notes while preserving history. `memory:review` presents uncertain, stale, contradictory, orphaned, or duplicate items. `memory:doctor` reports structural problems without silently changing meaning.

### Session end

The hook writes a complete session overview, links it to touched entities and source files where appropriate, extracts candidate memories, records decisions and prospective items, and writes an auditable journal entry. Hook failures must not prevent the main coding session from completing; failures are reported and retryable.

## 7. Retrieval design

Retrieval uses a layered strategy:

1. Exact text, aliases, tags, and path search.
2. Metadata filtering by type, entity, project, status, confidence, and time.
3. Ranking by relevance, recency, importance, confidence, and explicit applicability.
4. Graph expansion through typed relations and source sessions.
5. Optional embedding search and provider-based summarization.

The result assembler deduplicates overlapping notes, applies a context/token budget, preserves source links, labels each item by type and confidence, and states when evidence conflicts or is incomplete. Offline mode uses only vault text and local metadata. Optional providers must be replaceable adapters and may only create derived artifacts or explicitly approved canonical notes.

## 8. Plugin commands and skill decomposition

The plugin exposes:

- `memory:init` — initialize or validate a vault;
- `memory:save` — create a typed memory or entity;
- `memory:recall` — search and assemble linked context;
- `memory:session` — create, inspect, or summarize a session;
- `memory:project`, `memory:person`, `memory:agent` — manage entities;
- `memory:review` — inspect candidates, conflicts, stale notes, and promotions;
- `memory:doctor` — report broken links, invalid frontmatter, orphans, and consistency issues.

The portable skill is one entry skill with focused subskills for capture, retrieval, session overview, each memory type, entities, relations, review, privacy, and maintenance. Subskills must defer to the shared schemas and avoid platform-specific assumptions.

## 9. Privacy, safety, and failure handling

- No network access is required.
- Provider use is explicit and configurable.
- Secret detection and redaction run before persistence.
- Users can mark text, files, folders, projects, or sessions as excluded.
- Personal and high-impact claims require confirmation when confidence is uncertain.
- Retrieved context always identifies its source note and confidence.
- Atomic writes, journal entries, and backups protect against interrupted operations.
- Malformed notes are skipped and reported, not destroyed.
- Hooks fail open for the coding workflow: a memory failure cannot block the primary user task.

## 10. Acceptance criteria

1. A fresh vault initializes with the documented structure, templates, configuration, and schema version.
2. A session produces a readable overview containing context, work, decisions, discoveries, unresolved questions, and follow-ups.
3. Session extraction creates linked candidate memories with source-session references.
4. `memory:recall` returns relevant notes using offline exact/metadata retrieval and includes source links and confidence.
5. Project, user, and agent context can be created, linked, and loaded at session start.
6. Every memory type has a usable template and classification rule.
7. Typed relations support graph traversal and preserve contradictions/supersession history.
8. `memory:doctor` detects invalid frontmatter, broken links, orphaned managed notes, duplicate IDs, stale items, and contradictions.
9. Secret filtering, ignore markers, folder policies, atomic writes, and retryable journaling are covered by tests.
10. Offline operation works without provider credentials or network access.
11. Optional embedding/summarization providers can be added without changing canonical schemas.

## 11. Incremental implementation boundary

Although the workspace is designed as a full system, implementation should proceed in vertical slices: first the schema/configuration and initialization path, then entity and memory writes, then session summaries, then offline retrieval, then review/doctor, and finally optional providers. Each slice must keep the vault readable and preserve backward-compatible schema migration paths.
