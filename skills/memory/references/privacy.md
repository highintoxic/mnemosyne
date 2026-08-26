# Privacy rules

Memory capture is local-first and does not require network access. Before writing, redact GitHub/OpenAI-style keys, bearer tokens, credential assignments, and private-key blocks. Configured regular expressions are also applied. Redactions are recorded as labels in the journal, never as the original secret.

Honor `<!-- memory:ignore -->` and `[memory:ignore]` markers. Configure excluded paths in `.memory/config.json`; never capture from excluded folders. Ask for confirmation before promoting uncertain personal or high-impact claims. Retrieved context must retain its source path, type, and confidence so the user can inspect it.

Malformed notes are skipped and reported by `doctor`; they are never silently rewritten. Hooks fail open: a failed memory operation must not block the primary Claude Code workflow. Markdown is canonical, and disposable indexes may be deleted and rebuilt.
