#!/usr/bin/env sh
# mnemosyne universal session-end hook.
#
# Finalizes the session started by session-start.sh (if a session ID was
# persisted), building the overview automatically from journal events.
# FAIL-OPEN: never blocks the harness.
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

echo "[$(date -u +%FT%TZ)] session-end" >> "$LOGFILE" 2>&1

SESSION_ID="${MNEMOSYNE_SESSION_ID:-}"
if [ -z "$SESSION_ID" ] && [ -f "$MNEMOSYNE_VAULT/.memory/current-session.txt" ]; then
  SESSION_ID=$(cat "$MNEMOSYNE_VAULT/.memory/current-session.txt" 2>/dev/null | tr -d '[:space:]')
fi

if [ -n "$SESSION_ID" ]; then
  # Build the overview automatically from journaled memory/relation events.
  mnemosyne session --vault "$MNEMOSYNE_VAULT" finalize \
    --id "$SESSION_ID" --auto >> "$LOGFILE" 2>&1
  rm -f "$MNEMOSYNE_VAULT/.memory/current-session.txt"
fi

# Always leave the log clean for the harness.
exit 0
