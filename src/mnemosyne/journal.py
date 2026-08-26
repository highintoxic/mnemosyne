from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path


class Journal:
    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, event: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()
