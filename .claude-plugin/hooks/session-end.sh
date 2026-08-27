#!/usr/bin/env sh
# mnemosyne universal session-end hook.
#
# Finalizes the session started by session-start.sh, building the overview
# automatically from journal events. `finalize` clears this session's marker;
# markers belonging to other concurrent sessions are left alone.
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
if [ -z "$SESSION_ID" ]; then
  SESSION_ID=$(mnemosyne session --vault "$MNEMOSYNE_VAULT" current 2>/dev/null | tr -d '[:space:]')
fi

if [ -n "$SESSION_ID" ]; then
  mnemosyne session --vault "$MNEMOSYNE_VAULT" finalize \
    --id "$SESSION_ID" --auto >> "$LOGFILE" 2>&1
fi

# Always leave the log clean for the harness.
exit 0
