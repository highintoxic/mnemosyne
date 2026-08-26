#!/usr/bin/env sh
# obsidian-memory universal session-end hook.
#
# Finalizes the session started by session-start.sh (if a session ID was
# persisted), building the overview automatically from journal events.
# FAIL-OPEN: never blocks the harness.
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

echo "[$(date -u +%FT%TZ)] session-end" >> "$LOGFILE" 2>&1

SESSION_ID="${OBSIDIAN_MEMORY_SESSION_ID:-}"
if [ -z "$SESSION_ID" ] && [ -f "$OBSIDIAN_MEMORY_VAULT/.memory/current-session.txt" ]; then
  SESSION_ID=$(cat "$OBSIDIAN_MEMORY_VAULT/.memory/current-session.txt" 2>/dev/null | tr -d '[:space:]')
fi

if [ -n "$SESSION_ID" ]; then
  # Build the overview automatically from journaled memory/relation events.
  obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" finalize \
    --id "$SESSION_ID" --auto >> "$LOGFILE" 2>&1
  rm -f "$OBSIDIAN_MEMORY_VAULT/.memory/current-session.txt"
fi

# Always leave the log clean for the harness.
exit 0
