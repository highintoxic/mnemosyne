#!/usr/bin/env sh
# Hooks fail open so memory failures never block the coding session.
set +e
if [ -n "${OBSIDIAN_MEMORY_VAULT:-}" ] && command -v obsidian-memory >/dev/null 2>&1; then
  LOG="${OBSIDIAN_MEMORY_LOG:-$OBSIDIAN_MEMORY_VAULT/.memory/hooks.log}"
  if [ -n "${OBSIDIAN_MEMORY_SESSION_ID:-}" ]; then
    obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" finalize --id "$OBSIDIAN_MEMORY_SESSION_ID" --auto >> "$LOG" 2>&1
  fi
  obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" context --project "${OBSIDIAN_MEMORY_PROJECT:-}" >> "$LOG" 2>&1
fi
exit 0
