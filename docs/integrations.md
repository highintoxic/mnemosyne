# Harness Integrations

The memory workspace works with **any agent or harness** through three mechanisms:

| Mechanism | What it does | Works with |
|---|---|---|
| **MCP server** (`mnemosyne-mcp`) | Exposes all 13 memory operations as MCP tools; the harness discovers and calls them, and the agent can retrieve context on demand | Any MCP-capable client: Claude Code, Codex, Cursor, Gemini CLI, OpenCode, custom MCP clients |
| **Universal hooks** (`hooks/session-start.sh`, `hooks/session-end.sh`) | Auto-start a session, load context, and auto-finalize it from the journal — fail-open | Any harness that can run commands at session start/end, or a shell wrapper around `code` / `claude` / `codex` |
| **CLI** (`mnemosyne`) | Direct commands for scripts, cron, and manual use | Everything |

## 1. MCP server (recommended for agent-driven retrieval)

Register the MCP server with any MCP client:

### Claude Code

```json
// .claude/settings.json or ~/.claude/settings.json
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

### Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.mnemosyne]
command = "mnemosyne-mcp"
args = ["C:/Memory"]
```

### Cursor

Settings → MCP → Add server:

```
command: mnemosyne-mcp
args: ["C:/Memory"]
```

### Gemini CLI

```bash
gemini mcp add mnemosyne -- command "mnemosyne-mcp" "C:/Memory"
```

### Any MCP client (generic)

```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "mnemosyne-mcp",
      "args": ["C:/Memory"]
    }
  }
}
```

Once registered, the agent sees 13 tools: `init`, `save`, `recall`, `entity`,
`session_start`, `session_finalize`, `session_context`, `promote`, `reject`,
`supersede`, `review`, `doctor`. Ask it to "recall relevant memory"
or it will do so automatically at session start when configured.

## 2. Universal hooks (auto start/end every session)

### Shell wrapper (works with ANY harness)

Wrap your agent command so every session triggers memory hooks:

```bash
# ~/bin/agent.sh — wrap claude, codex, cursor, gemini...
#!/usr/bin/env sh
export MNEMOSYNE_VAULT="C:/Memory"
export MNEMOSYNE_PROJECT="${1:-}"
export MNEMOSYNE_PRINT_CONTEXT=1   # inject context into the model
sh /c/Projects/mnemosyne/hooks/session-start.sh
"$@"                                   # run the actual agent
sh /c/Projects/mnemosyne/hooks/session-end.sh
```

```bash
chmod +x ~/bin/agent.sh
agent.sh claude                       # or: agent.sh codex, agent.sh cursor ...
```

At start it creates a session note and loads recent context; at end it
auto-finalizes the session with a complete overview built from the journal.

### Claude Code plugin hooks (already included)

`.claude-plugin/hooks/session-start.sh` and `session-end.sh` do the same for
Claude Code natively, reading `MNEMOSYNE_VAULT` / `MNEMOSYNE_SESSION_ID`.

### Codex CLI (`~/.codex/config.toml`)

```toml
[hooks]
SessionStart = { command = "sh /c/Projects/mnemosyne/hooks/session-start.sh" }
SessionEnd   = { command = "sh /c/Projects/mnemosyne/hooks/session-end.sh" }
```

## 3. CLI (direct, scriptable)

```bash
mnemosyne --vault C:/Memory recall "project conventions"
mnemosyne --vault C:/Memory save --type semantic --title "X" --body "Y"
mnemosyne --vault C:/Memory session context --project research
```

## Environment variables (all mechanisms)

| Variable | Purpose |
|---|---|
| `MNEMOSYNE_VAULT` | Vault path (default `C:/Memory`) |
| `MNEMOSYNE_PROJECT` | Scope context to a project entity |
| `MNEMOSYNE_USER` | Active user entity ID |
| `MNEMOSYNE_AGENT` | Active agent entity ID |
| `MNEMOSYNE_SESSION_ID` | Session to finalize (end hook) |
| `MNEMOSYNE_PRINT_CONTEXT` | `1` = print context to stdout at start (direct model injection) |
| `MNEMOSYNE_LOG` | Log file for hook failures (default `vault/.memory/hooks.log`) |

## Retrieval behavior inside the agent

When an agent calls `recall`, it gets bounded, source-linked results:

```
[semantic] Atomic writes (memories/semantic/atomic-writes-....md, confidence=0.9)
Use atomic Markdown writes with replace operations.
```

- Exact + metadata matching always works offline.
- `--semantic` / `semantic: true` blends TF-IDF ranking.
- Related notes are pulled in through typed relations (graph expansion).
- Results include the source path and confidence so the agent can cite them.

## Automatic session linking (keeps memories up to date)

While a session is active (started by the hooks, tracked in `vault/.memory/current-session.txt`), every `save` via the MCP server **automatically attaches the active session** to `source_sessions` — so every memory written during a session is traceable back to it. At session end, the overview's Work section lists all memories created in that window.

To disable auto-linking for a specific save, pass `source_sessions: []` explicitly.

## Verified

The MCP stdio server was verified with a live `initialize` → `tools/call save`
→ `tools/call recall` round trip (13 tools listed, memory created and
retrieved). All 34+ tests pass. The user-level Claude Code hooks were
verified under `cmd` exactly as Claude Code invokes them: session-start
creates the marker, session-end finalizes to `status: complete`.
