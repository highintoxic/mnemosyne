# Obsidian Memory Workspace

Local-first linked memory for Claude Code and Obsidian. The canonical store is human-readable Markdown with YAML frontmatter in an Obsidian vault. The implementation lives separately from the vault:

```text
C:/Projects/obsidian-memory  # this project: CLI, skill, plugin, tests
C:/Memory                    # example configured Obsidian vault
```

## Install

Requires Python 3.11+. From this project:

```bash
python -m pip install -e .
obsidian-memory init --vault C:/Memory
```

If `--vault` is omitted, the CLI uses `OBSIDIAN_MEMORY_VAULT` or `C:/Memory`.

## Common operations

```bash
obsidian-memory entity --vault C:/Memory project --title "Research"
obsidian-memory entity --vault C:/Memory agent --title "Claude"
obsidian-memory save --vault C:/Memory --type semantic --title "Canonical store" --body "Markdown is authoritative."
obsidian-memory recall --vault C:/Memory "canonical store"
obsidian-memory recall --vault C:/Memory "atomic operations" --semantic   # TF-IDF ranking blend
obsidian-memory session --vault C:/Memory start --project research
obsidian-memory session --vault C:/Memory finalize --id SESSION_ID --overview '{"goals":["ship"],"decisions":["stay local"],"work":["implemented"],"discoveries":[],"unresolved":[],"follow_ups":[]}'
obsidian-memory session --vault C:/Memory finalize --id SESSION_ID --auto --decisions "stay local"  # build overview from the journal
obsidian-memory review --vault C:/Memory
obsidian-memory review --vault C:/Memory --promote NOTE_ID      # candidate -> active
obsidian-memory review --vault C:/Memory --reject NOTE_ID       # candidate -> rejected
obsidian-memory save --vault C:/Memory --type semantic --title "Updated fact" --body "..." --supersede OLD_NOTE_ID
obsidian-memory index --vault C:/Memory
obsidian-memory doctor --vault C:/Memory
```

Set `OBSIDIAN_MEMORY_SESSION_ID` for Claude Code lifecycle hooks; the session-end hook then auto-finalizes that session from the journal (fail-open).

The Claude Code integration is in `.claude-plugin/`; the portable entry skill is `skills/memory/SKILL.md`. Set `OBSIDIAN_MEMORY_VAULT=C:/Memory` and optionally `OBSIDIAN_MEMORY_PROJECT` before enabling lifecycle hooks. Hooks are defensive and fail open.

## Any agent / harness (MCP + universal hooks)

The system is not limited to Claude Code. It exposes:

- **MCP server** (`obsidian-memory-mcp`) — 13 memory tools over the Model Context Protocol; register it with Claude Code, Codex, Cursor, Gemini CLI, or any MCP client and the agent can save/recall/relate memory on demand.
- **Universal hooks** (`hooks/session-start.sh`, `hooks/session-end.sh`) — run at session start/end in any harness; they auto-start a session, inject relevant context, and auto-finalize the overview from the journal.

See [docs/integrations.md](docs/integrations.md) for per-harness setup (JSON/Toml snippets for Claude Code, Codex, Cursor, Gemini CLI, shell wrappers) and the environment-variable reference.

## Design guarantees

- Offline operation works without provider credentials.
- Typed semantic, episodic, procedural, prospective, parametric, and retrieval memory is supported.
- Projects, users, agents, sessions, relations, confidence, and source links are represented in the vault.
- Lifecycle: candidates can be promoted/rejected via `review`; `--supersede` marks old notes superseded and links them with a `supersedes` relation.
- `recall --semantic` blends a stdlib TF-IDF provider into ranking; custom providers implement `SemanticProvider.search`.
- `.memory/index` is disposable; Markdown notes remain authoritative.
- `doctor` reports malformed notes, broken links, orphans, invalid statuses, duplicates, stale notes, and contradiction markers.
