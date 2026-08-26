<div align="center">

# 🧠 Mnemosyne

**The memory layer for AI agents — backed by your Obsidian vault.**

Local-first, human-readable, graph-connected memory that any agent or harness
can read, write, and retrieve — automatically, on every session.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Zero network required](https://img.shields.io/badge/offline-first-success)](#design)

</div>

---

## Why Mnemosyne?

Agents are amnesiacs. Every new session, they forget what you decided, what you
learned, what they built — and you repeat yourself. Existing memory systems lock
you into a proprietary database or a vendor's cloud.

Mnemosyne gives agents **real memory that lives in your own vault**:

- **Obsidian Markdown is the source of truth.** Every memory is a readable note
  you can open, edit, and link by hand. No lock-in, no database to migrate.
- **Any agent, any harness.** MCP server, universal session hooks, and a CLI —
  works with Claude Code, Codex, Cursor, Gemini CLI, and anything else.
- **Automatic and continuous.** Session hooks start, track, and finalize every
  session. Memories are created *during* work, not just at the end.
- **Graph-native.** Typed relations light up Obsidian's Graph View and power
  graph-expanded retrieval.
- **Offline-first.** Exact + TF-IDF retrieval works with zero network access.

---

## Features

### 🗂️ Eight memory types
| Type | Stores | Example |
|---|---|---|
| `semantic` | durable facts & conclusions | "This project requires Python 3.12" |
| `episodic` | what happened | "Tried X; failed because Y" |
| `procedural` | how to do something | "Deploy: run A, then B" |
| `prospective` | future intentions | "Bump deps after release" |
| `parametric` | preferences & conventions | "User prefers concise answers" |
| `retrieval` | saved queries & hints | "For auth questions, see [[x]] [[y]]" |
| `question` | quiz/probe Q&A with correctness | "What is atomicity? → all-or-nothing ✓" |
| `decision` | decisions with rationale | "Use Markdown; options, choice, why" |

### 🔗 Typed relations
`supports · contradicts · derived-from · implements · blocked-by · supersedes · part-of · applies-to · related-to` — first-class notes with wiki-links, so the whole vault connects in **Obsidian's Graph View**.

### 🤖 Automatic session lifecycle
```
SessionStart      → create session, inject relevant context
UserPromptSubmit  → log every prompt, inject per-prompt memory
(save/update)     → memories auto-link to the active session
SessionEnd        → auto-finalize: overview built from the journal
```
All hooks are **fail-open** — memory can never block your work.

### 🔍 Retrieval that cites its sources
Exact match → metadata filters → TF-IDF semantic blend → graph expansion. Every result carries type, confidence, score, and source path, so the agent can tell you *where* it learned something.

### 🛡️ Privacy by default
Secrets auto-redacted before write, `<!-- memory:ignore -->` markers, per-folder exclusion, confirmation for uncertain personal facts, JSONL journal audit trail, atomic writes.

---

## Quick start

```bash
# Install
python -m pip install mnemosyne          # or: pip install -e . from the repo

# Initialize a vault (creates the folder layout; never deletes existing files)
mnemosyne init --vault C:/Memory

# Save and recall
mnemosyne save --type semantic --title "Canonical store" --body "Markdown is authoritative."
mnemosyne recall "canonical store"
```

Requires **Python 3.11+**. Zero runtime dependencies.

---

## Usage

### CLI

```bash
mnemosyne init                              # initialize a vault
mnemosyne save     --type semantic --title T --body B [--status] [--confidence] [--supersede OLD]
mnemosyne update    --id ID [--body] [--title] [--confidence]
mnemosyne recall    "query" [--type] [--semantic] [--limit]
mnemosyne entity    project|user|agent --title T [--description]
mnemosyne question  --question Q --answer A [--correct] [--topic] [--difficulty]
mnemosyne decision  --decision D --rationale R [--context] [--options ...] [--chosen]
mnemosyne session   start|update|finalize|context
mnemosyne review    [--promote ID] [--reject ID]
mnemosyne index     # rebuild disposable search index
mnemosyne doctor    # diagnose broken links, orphans, contradictions
```

### MCP server — for any agent

Register `mnemosyne-mcp` with any MCP client and the agent gets 17 tools:

```
init · save · update · recall · entity · log_question · log_decision ·
session_start · session_update · session_finalize · session_context ·
promote · reject · supersede · review · index · doctor
```

```jsonc
// Claude Code — .claude/settings.json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "mnemosyne-mcp",
      "args": ["C:/Memory"],
      "env": { "MNEMOSYNE_VAULT": "C:/Memory" }
    }
  }
}
```

### Universal hooks — automatic on every session

```bash
sh hooks/session-start.sh   # session start: create + context injection
sh hooks/session-prompt.sh  # every prompt: log activity + inject memory
sh hooks/session-end.sh     # session end: auto-finalize overview
```

See [docs/integrations.md](docs/integrations.md) for per-harness setup
(Claude Code, Codex, Cursor, Gemini CLI, shell wrappers) and the full
environment-variable reference.

---

## Architecture

```text
Any agent / harness
   │  MCP (mnemosyne-mcp) · hooks (shell) · CLI
   ▼
mnemosyne  (Python, stdlib-only)
   │  config · notes (atomic) · privacy · journal
   │  entities · memories · sessions · relations
   │  retrieval (exact + TF-IDF) · maintenance
   ▼
Obsidian vault (canonical Markdown + YAML)
   ├── entities/{users,projects,agents}
   ├── sessions/
   ├── memories/{semantic,episodic,procedural,prospective,parametric,retrieval,questions,decisions}
   ├── relations/
   ├── templates/  reviews/  indexes/        ← indexes are disposable
   └── .memory/    config · journal · session marker
```

Markdown is **authoritative**; `.memory/` (config, journal, indexes) is
operational or derived — delete it and rebuild, never lose a memory.

---

## Skill cooperation

Mnemosyne ships a portable agent skill (`skills/memory/`) with references for
schemas, privacy, and skill integration. Learning/quiz/probe skills record
into it through `log_question` and `log_decision`, making past questions,
misses, and decisions durable, re-testable memory.

---

## Development

```bash
python -m pip install -e .
python -m pytest -q        # 45+ tests, stdlib only
python -m compileall -q src
```

- **TDD**: write the failing test, watch it fail, implement, watch it pass.
- Commits follow Conventional Commits.
- See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Project layout

```text
src/mnemosyne/          # core package (stdlib only)
  cli.py                # CLI entry point
  mcp.py                # MCP stdio server
  store.py              # entities, memories, records
  sessions.py           # session lifecycle + activity log
  relations.py          # typed relations
  retrieval.py          # exact + graph retrieval
  providers.py          # TF-IDF semantic provider (pluggable)
  privacy.py            # secret redaction, ignore markers
  journal.py            # JSONL audit trail
  maintenance.py        # review / index / doctor
hooks/                  # universal session hooks (fail-open)
skills/memory/          # portable agent skill
.claude-plugin/         # Claude Code plugin manifest + hooks
docs/integrations.md    # per-harness setup
```

---

## Roadmap

- [ ] Embedding providers behind the existing `SemanticProvider` protocol (local & remote)
- [ ] Obsidian community UI plugin (Graph filters, dashboards)
- [ ] Spaced-repetition deck view from `question` records

---

## License

[MIT](LICENSE) © highintoxic

Contributions, issues, and ideas welcome — open an issue or PR!
