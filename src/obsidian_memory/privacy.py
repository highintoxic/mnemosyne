from __future__ import annotations
import re

DEFAULT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("github-token", r"\b(?:gh[pousr]_[A-Za-z0-9_\-]{20,})\b"),
    ("openai-key", r"\bsk-[A-Za-z0-9]{20,}\b"),
    ("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
    ("bearer-token", r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    ("credential-assignment", r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[=:]\s*[^\s]+"),
)


def redact_sensitive(text: str, extra_patterns: list[str] | None = None) -> tuple[str, list[str]]:
    findings: list[str] = []
    result = text
    patterns = list(DEFAULT_PATTERNS) + [("custom", pattern) for pattern in (extra_patterns or [])]
    for label, pattern in patterns:
        result, count = re.subn(pattern, "[REDACTED]", result, flags=re.DOTALL if label == "private-key" else 0)
        if count:
            findings.append(label)
    return result, findings


def is_ignored(text: str, markers: tuple[str, ...] = ("<!-- memory:ignore -->", "[memory:ignore]")) -> bool:
    return any(marker in text for marker in markers)
