"""Memory taxonomy shared by the CLI, skill, and vault schemas."""

MEMORY_TYPES = {
    "semantic": "durable facts, concepts, and conclusions",
    "episodic": "events, experiments, decisions, and outcomes",
    "procedural": "repeatable workflows and instructions",
    "prospective": "future actions, reminders, and triggers",
    "parametric": "declared preferences, capabilities, and constraints",
    "retrieval": "saved queries, aliases, and context assembly hints",
}


def classify(kind: str) -> str:
    """Return the definition for a supported memory type."""
    try:
        return MEMORY_TYPES[kind.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported memory type: {kind}") from exc
