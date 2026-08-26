#!/usr/bin/env sh
# Hooks fail open so memory failures never block the coding session.
set +e
if [ -n "${OBSIDIAN_MEMORY_VAULT:-}" ] && command -v obsidian-memory >/dev/null 2>&1; then
  obsidian-memory session --vault "$OBSIDIAN_MEMORY_VAULT" context --project "${OBSIDIAN_MEMORY_PROJECT:-}" >> "${OBSIDIAN_MEMORY_LOG:-$OBSIDIAN_MEMORY_VAULT/.memory/hooks.log}" 2>&1
fi
exit 0
