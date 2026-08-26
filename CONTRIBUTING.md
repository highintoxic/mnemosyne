# Contributing to Mnemosyne

Thanks for contributing! This project keeps a small, deliberate surface — see
the philosophy below before opening a PR.

## Philosophy

- **Simplicity first.** Minimum code that solves the problem. Nothing
  speculative. If a feature needs 200 lines and could be 50, rewrite it.
- **Stdlib-only core.** The core package (`src/mnemosyne/`) has zero runtime
  dependencies and works offline. New features should stay dependency-light.
- **Markdown is canonical.** Vault notes are the source of truth. Never put
  essential state in a database, index, or cache that isn't rebuildable from
  the notes.
- **Fail-open.** Hooks and integrations must never block the user's primary
  work. Memory failures are logged, not fatal.

## Development setup

```bash
python -m pip install -e .
python -m pytest -q
```

## TDD workflow

Follow strict test-driven development:

1. Write the failing test (in `tests/`) that describes the behavior.
2. Run it and confirm it fails for the right reason.
3. Write the minimal implementation.
4. Run the full suite: `python -m pytest -q`
5. Commit with a Conventional Commit message:

```text
feat: add question record type
fix: redact relation evidence before write
docs: update skill integration reference
refactor: extract provider protocol
test: cover session activity preservation
```

## What to check before submitting

- [ ] Full test suite passes (`python -m pytest -q`)
- [ ] `python -m compileall -q src` is clean
- [ ] New behavior is covered by a test that fails without the change
- [ ] No new runtime dependencies
- [ ] Existing vaults remain compatible (schema version preserved, additive only)
- [ ] Docs updated where behavior is user-facing (README, skill, integrations)

## Code style

- Python 3.11+, `from __future__ import annotations`
- Type hints on all public functions
- No third-party imports in `src/mnemosyne/` unless unavoidable and discussed
- Match the existing style of the file you're editing

## Questions

Open an issue with a minimal reproduction. Feature ideas are welcome as issues
first — discuss before building, especially if it touches the vault schema.
