# `/memory` command

Use the `obsidian-memory` CLI against `$OBSIDIAN_MEMORY_VAULT` (default example: `C:/Memory`).

- `/memory init` → `obsidian-memory init --vault "$OBSIDIAN_MEMORY_VAULT"`
- `/memory save` → classify content, redact secrets, then call `save` with a supported memory type.
- `/memory recall <query>` → call `recall`; include source paths, confidence, and memory types.
- `/memory session` → start/finalize a complete session overview.
- `/memory project|person|agent` → call `entity` with the corresponding kind.
- `/memory review|index|doctor` → call the maintenance subcommand.

Never write secrets. Honor `<!-- memory:ignore -->`, excluded paths, and confirmation requirements for uncertain personal claims. Markdown notes are canonical; `.memory/index` is disposable.
