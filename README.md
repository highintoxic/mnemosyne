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
obsidian-memory session --vault C:/Memory start --project research
obsidian-memory session --vault C:/Memory finalize --id SESSION_ID --overview '{"goals":["ship"],"decisions":["stay local"],"work":["implemented"],"discoveries":[],"unresolved":[],"follow_ups":[]}'
obsidian-memory review --vault C:/Memory
obsidian-memory index --vault C:/Memory
obsidian-memory doctor --vault C:/Memory
```

The Claude Code integration is in `.claude-plugin/`; the portable entry skill is `skills/memory/SKILL.md`. Set `OBSIDIAN_MEMORY_VAULT=C:/Memory` and optionally `OBSIDIAN_MEMORY_PROJECT` before enabling lifecycle hooks. Hooks are defensive and fail open.

## Design guarantees

- Offline operation works without provider credentials.
- Typed semantic, episodic, procedural, prospective, parametric, and retrieval memory is supported.
- Projects, users, agents, sessions, relations, confidence, and source links are represented in the vault.
- `.memory/index` is disposable; Markdown notes remain authoritative.
- `doctor` reports malformed notes, broken links, orphans, invalid statuses, duplicates, stale notes, and contradiction markers.
