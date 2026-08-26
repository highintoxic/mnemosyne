from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

DEFAULT_FOLDERS = (
    "entities/users", "entities/projects", "entities/agents", "sessions",
    "memories/semantic", "memories/episodic", "memories/procedural",
    "memories/prospective", "memories/parametric", "memories/retrieval",
    "memories/questions", "memories/decisions",
    "relations", "indexes", "reviews", "templates", ".memory/journal", ".memory/index",
)


@dataclass
class VaultConfig:
    vault: Path
    schema_version: int = 1
    folders: list[str] = field(default_factory=lambda: list(DEFAULT_FOLDERS))
    ignore_markers: list[str] = field(default_factory=lambda: ["<!-- memory:ignore -->", "[memory:ignore]"])
    excluded_paths: list[str] = field(default_factory=list)
    sensitive_patterns: list[str] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return self.vault / ".memory" / "config.json"

    @classmethod
    def initialize(cls, vault: Path) -> "VaultConfig":
        vault = Path(vault).expanduser().resolve()
        vault.mkdir(parents=True, exist_ok=True)
        config = cls(vault)
        for folder in config.folders:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        if not config.path.exists():
            payload = asdict(config)
            payload.pop("vault")
            _atomic_json(config.path, payload)
        for kind in ("semantic", "episodic", "procedural", "prospective", "parametric", "retrieval", "question", "decision"):
            template = vault / "templates" / f"{kind}.md"
            if not template.exists():
                template.write_text(f"---\nmemory_schema: 1\ntype: {kind}\nstatus: candidate\n---\n\n# {{{{title}}}}\n", encoding="utf-8")
        return cls.load(vault)

    @classmethod
    def load(cls, vault: Path) -> "VaultConfig":
        vault = Path(vault).expanduser().resolve()
        path = vault / ".memory" / "config.json"
        if not path.exists():
            raise FileNotFoundError(f"Memory vault is not initialized: {vault}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(vault=vault, **data)

    def is_path_excluded(self, path: Path) -> bool:
        relative = str(path.resolve().relative_to(self.vault)).replace("\\", "/")
        return any(relative == item.rstrip("/") or relative.startswith(item.rstrip("/") + "/") for item in self.excluded_paths)


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
    temp.replace(path)
