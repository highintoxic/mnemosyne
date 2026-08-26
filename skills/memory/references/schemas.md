# Canonical schemas

Managed Markdown notes begin and end YAML frontmatter with `memory_schema: 1`, a stable `id`, `type`, `title`, `status`, `created`, and `updated`. Memory notes also carry `confidence`, `importance`, `tags`, and optional `source_sessions`, `entities`, and `related` links.

## Types

- `semantic`: durable facts, concepts, definitions, and conclusions.
- `episodic`: events, experiments, decisions, and outcomes.
- `procedural`: repeatable workflows and instructions.
- `prospective`: intended actions, reminders, triggers, and deadlines.
- `parametric`: approved preferences, conventions, capabilities, and constraints.
- `retrieval`: saved queries, aliases, and context-assembly hints.

Entity types are `user`/`person`, `project`, and `agent`; sessions use `type: session`; relations use `type: relation` with `source`, `relation`, and `target` fields. IDs are independent of filenames so Obsidian renames are safe. Canonical note content stays human-readable Markdown. `.memory/config.json`, JSONL journal events, and `.memory/index` are operational/derived files.

## Links and lifecycle

Use Obsidian wikilinks (`[[path-or-id]]`) for source sessions, entities, related notes, and relation body references. Status values are `candidate`, `active`, `complete`, `superseded`, `archived`, or `rejected`. New evidence can supersede an old note; contradictory notes remain present and are reviewed rather than overwritten.
