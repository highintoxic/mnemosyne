#!/usr/bin/env sh
# obsidian-memory universal session hook.
#
# Works with ANY agent/harness that can run a command at session start/end
# (Claude Code, Codex, Cursor, Gemini CLI, shell wrappers, etc.).
#
# Usage:
#   OBSIDIAN_MEMORY_VAULT=C:/Memory \
#   OBSIDIAN_MEMORY_PROJECT=my-project \
#   sh hooks/session-start.sh
#
# At start: loads relevant context into a file the harness can read,
#           and optionally prints it to stdout for injection.
#
# Environment:
#   OBSIDIAN_MEMORY_VAULT   (required) vault path, e.g. C:/Memory
#   OBSIDIAN_MEMORY_PROJECT (optional) project entity ID to scope context
#   OBSIDIAN_MEMORY_AGENT   (optional) agent entity ID
#   OBSIDIAN_MEMORY_USER    (optional) user entity ID
#   OBSIDIAN_MEMORY_SESSION_ID (optional, end only) session note ID to finalize
#   OBSIDIAN_MEMORY_LOG     (optional) log file for failures (default: vault/.memory/hooks.log)
#
# Hooks are FAIL-OPEN: any failure is logged and the script exits 0.
set +e
LOGFILE="${OBSIDIAN_MEMORY_LOG:-$OBSIDIAN_MEMORY_VAULT/.memory/hooks.log}"
mkdir -p "$(dirname "$LOGFILE")" 2>/dev/null

if [ -z "${OBSIDIAN_MEMORY_VAULT:-}" ]; then
  echo "obsidian-memory: OBSIDIAN_MEMORY_VAULT not set; skipping" >> "$LOGFILE" 2>&1
  exit 0
fi

if ! command -v obsidian-memory >/dev/null 2>&1; then
  echo "obsidian-memory: CLI not on PATH; skipping" >> "$LOGFILE" 2>&1
  exit 0
fi

echo "[$(date -u +%FT%TZ)] session-start for ${OBSIDIAN_MEMORY_PROJECT:-all-projects}" >> "$LOGFILE" 2>&1

# Start a session and remember its ID for the end hook.
SESSION_ID=$(obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" start \
  --project "${OBSIDIAN_MEMORY_PROJECT:-}" \
  --user "${OBSIDIAN_MEMORY_USER:-}" \
  --agent "${OBSIDIAN_MEMORY_AGENT:-}" 2>>"$LOGFILE" | sed 's/.*[\\\/]//; s/\.md$//' | tr -d '[:space:]')

if [ -n "$SESSION_ID" ]; then
  # Persist the session ID so the session-end hook can finalize this session.
  echo "$SESSION_ID" > "$OBSIDIAN_MEMORY_VAULT/.memory/current-session.txt"
fi

# Load relevant context: recent sessions + semantic recall of open context.
obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" context \
  --project "${OBSIDIAN_MEMORY_PROJECT:-}" --limit 10 >> "$LOGFILE" 2>&1

# Optionally print context to stdout for direct injection into the model.
if [ "${OBSIDIAN_MEMORY_PRINT_CONTEXT:-0}" = "1" ]; then
  echo "=== MEMORY CONTEXT ==="
  obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" context \
    --project "${OBSIDIAN_MEMORY_PROJECT:-}" --limit 5 2>/dev/null
fi

exit 0
