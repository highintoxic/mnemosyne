#!/usr/bin/env sh
# mnemosyne UserPromptSubmit hook — fires on EVERY user prompt.
#
# 1. Ensures a session is active (lazy-start if the marker is missing).
# 2. Appends the prompt to the session's Activity Log (timestamped, redacted).
# 3. When MNEMOSYNE_PRINT_CONTEXT=1, prints up to
#    MNEMOSYNE_CONTEXT_LIMIT (default 3) memories relevant to the
#    prompt, so the agent receives fresh context mid-session.
#
# Claude Code passes the prompt as JSON on stdin:
#   {"prompt": "...", "stop_hook_active": bool}
# stdout is appended to the conversation context.
#
# FAIL-OPEN: never blocks the user's prompt.
set +e
LOGFILE="${MNEMOSYNE_LOG:-$MNEMOSYNE_VAULT/.memory/hooks.log}"
mkdir -p "$(dirname "$LOGFILE")" 2>/dev/null

if [ -z "${MNEMOSYNE_VAULT:-}" ] || ! command -v mnemosyne >/dev/null 2>&1; then
  exit 0
fi

# Read the prompt JSON from stdin.
PROMPT=""
if [ ! -t 0 ]; then
  PROMPT=$(cat 2>/dev/null | sed 's/.*"prompt"[[:space:]]*:[[:space:]]*"//' | sed 's/".*//' | head -c 2000)
fi

# Lazy-start a session if none is active.
SID=""
if [ -f "$MNEMOSYNE_VAULT/.memory/current-session.txt" ]; then
  SID=$(cat "$MNEMOSYNE_VAULT/.memory/current-session.txt" 2>/dev/null | tr -d '[:space:]')
fi
if [ -z "$SID" ]; then
  SID=$(mnemosyne session --vault "$MNEMOSYNE_VAULT" start \
    --project "${MNEMOSYNE_PROJECT:-}" 2>>"$LOGFILE" | sed 's/.*[\\\/]//; s/\.md$//' | tr -d '[:space:]')
  if [ -n "$SID" ]; then
    echo "$SID" > "$MNEMOSYNE_VAULT/.memory/current-session.txt"
  fi
fi

# Log the prompt as activity in the live session note.
if [ -n "$SID" ] && [ -n "$PROMPT" ]; then
  mnemosyne session --vault "$MNEMOSYNE_VAULT" update --id "$SID" \
    --text "user: $PROMPT" >> "$LOGFILE" 2>&1
fi

# Print relevant memory context for this prompt (mid-session retrieval).
if [ "${MNEMOSYNE_PRINT_CONTEXT:-0}" = "1" ] && [ -n "$PROMPT" ]; then
  LIMIT="${MNEMOSYNE_CONTEXT_LIMIT:-3}"
  mnemosyne recall --vault "$MNEMOSYNE_VAULT" "$PROMPT" --semantic --limit "$LIMIT" 2>/dev/null | head -n "$((LIMIT * 2))"
fi

exit 0
