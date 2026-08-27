# `/memory` command

Use the `mnemosyne` CLI against `$MNEMOSYNE_VAULT` (default example: `C:/Memory`).

- `/memory init` → `mnemosyne init --vault "$MNEMOSYNE_VAULT"`
- `/memory save` → classify content, redact secrets, then call `save` with a supported memory type.
- `/memory recall <query>` → call `recall`; include source paths, confidence, and memory types.
- `/memory session` → start/finalize a complete session overview.
- `/memory project|person|agent` → call `entity` with the corresponding kind.
- `/memory review|doctor` → call the maintenance subcommand.

Never write secrets. Honor `<!-- memory:ignore -->`, excluded paths, and confirmation requirements for uncertain personal claims. Markdown notes are canonical; `.memory/` is operational.
