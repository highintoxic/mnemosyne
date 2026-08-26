from datetime import datetime, timezone
import secrets
import re


def new_id(prefix: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", prefix.lower()).strip("-") or "note"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{clean}_{stamp}_{secrets.token_hex(4)}"
