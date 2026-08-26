from __future__ import annotations

from pathlib import Path
import json
import os
import re
import tempfile


def _scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _yaml_line(key: str, value: object) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        lines = [f"{key}:"]
        lines.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in value)
        return lines
    if isinstance(value, dict):
        lines = [f"{key}:"]
        lines.extend(f"  {sub}: {json.dumps(item, ensure_ascii=False)}" for sub, item in value.items())
        return lines
    text = _scalar(value)
    if isinstance(value, str) and (not value or re.search(r"[:#\[\]{},]|^[-?]|\s$", value)):
        text = json.dumps(value, ensure_ascii=False)
    return [f"{key}: {text}"]


def serialize_frontmatter(metadata: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.extend(_yaml_line(key, value))
    lines.append("---")
    return "\n".join(lines)


def _parse_value(text: str) -> object:
    text = text.strip()
    if text in ("[]", "{}"):
        return [] if text == "[]" else {}
    if text in ("true", "false"):
        return text == "true"
    if text == "null":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return float(text) if "." in text else int(text)
        except ValueError:
            return text.strip('"\'')


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---"):
        raise ValueError("note has no YAML frontmatter")
    lines = text.splitlines()
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc
    data: dict[str, object] = {}
    current: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.startswith("  - ") and current:
            data.setdefault(current, [])
            assert isinstance(data[current], list)
            data[current].append(_parse_value(line[4:]))
            continue
        if line.startswith("  ") and current and ":" in line:
            key, value = line.strip().split(":", 1)
            if not isinstance(data.get(current), dict):
                data[current] = {}
            data[current][key] = _parse_value(value)
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        current = key.strip()
        stripped = value.strip()
        data[current] = [] if not stripped else _parse_value(stripped)
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return data, body.rstrip("\n")


def write_note(path: Path, frontmatter: dict[str, object], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_frontmatter(frontmatter) + "\n\n" + body.rstrip() + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temp_name).replace(path)
    except BaseException:
        try:
            Path(temp_name).unlink()
        except FileNotFoundError:
            pass
        raise


def read_note(path: Path) -> tuple[dict[str, object], str]:
    return parse_frontmatter(Path(path).read_text(encoding="utf-8"))
