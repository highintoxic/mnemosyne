#!/usr/bin/env sh
# mnemosyne universal session hook.
#
# Works with ANY agent/harness that can run a command at session start/end
# (Claude Code, Codex, Cursor, Gemini CLI, shell wrappers, etc.).
#
# Usage:
#   MNEMOSYNE_VAULT=C:/Memory \
#   MNEMOSYNE_PROJECT=my-project \
#   sh hooks/session-start.sh
#
# At start: loads relevant context into a file the harness can read,
#           and optionally prints it to stdout for injection.
#
# Environment:
#   MNEMOSYNE_VAULT   (required) vault path, e.g. C:/Memory
#   MNEMOSYNE_PROJECT (optional) project entity ID; defaults to the directory name
#   MNEMOSYNE_AGENT   (optional) agent entity ID
#   MNEMOSYNE_USER    (optional) user entity ID
#   MNEMOSYNE_LOG     (optional) log file for failures (default: vault/.memory/hooks.log)
#
# Concurrent sessions are kept apart by a per-session marker the CLI writes,
# keyed by MNEMOSYNE_SESSION_KEY or CLAUDE_CODE_SESSION_ID.
#
# Hooks are FAIL-OPEN: any failure is logged and the script exits 0.
set +e
LOGFILE="${MNEMOSYNE_LOG:-$MNEMOSYNE_VAULT/.memory/hooks.log}"
mkdir -p "$(dirname "$LOGFILE")" 2>/dev/null

if [ -z "${MNEMOSYNE_VAULT:-}" ]; then
  echo "mnemosyne: MNEMOSYNE_VAULT not set; skipping" >> "$LOGFILE" 2>&1
  exit 0
fi

if ! command -v mnemosyne >/dev/null 2>&1; then
  echo "mnemosyne: CLI not on PATH; skipping" >> "$LOGFILE" 2>&1
  exit 0
fi

# Scope the session to a project. Harnesses run hooks in the project
# directory, so its name is the default project id.
MNEMOSYNE_PROJECT="${MNEMOSYNE_PROJECT:-$(basename "$PWD")}"

echo "[$(date -u +%FT%TZ)] session-start for $MNEMOSYNE_PROJECT" >> "$LOGFILE" 2>&1

# Start a session. The CLI writes the session marker itself, keyed to this
# harness session, so a second session cannot steal the first one's memories.
mnemosyne session --vault "$MNEMOSYNE_VAULT" start \
  --project "$MNEMOSYNE_PROJECT" \
  --user "${MNEMOSYNE_USER:-}" \
  --agent "${MNEMOSYNE_AGENT:-}" >> "$LOGFILE" 2>&1

# Load relevant context: recent sessions for this project.
mnemosyne session --vault "$MNEMOSYNE_VAULT" context \
  --project "$MNEMOSYNE_PROJECT" --limit 10 >> "$LOGFILE" 2>&1

# Optionally print context to stdout for direct injection into the model.
if [ "${MNEMOSYNE_PRINT_CONTEXT:-0}" = "1" ]; then
  echo "=== MEMORY CONTEXT ==="
  mnemosyne session --vault "$MNEMOSYNE_VAULT" context \
    --project "$MNEMOSYNE_PROJECT" --limit 5 2>/dev/null
fi

exit 0
