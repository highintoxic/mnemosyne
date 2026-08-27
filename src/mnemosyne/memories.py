"""Memory taxonomy shared by the CLI, skill, and vault schemas."""

MEMORY_TYPES = {
    "semantic": "durable facts, concepts, and conclusions",
    "episodic": "events, experiments, decisions, and outcomes",
    "procedural": "repeatable workflows and instructions",
    "prospective": "future actions, reminders, and triggers",
    "parametric": "declared preferences, capabilities, and constraints",
    "retrieval": "saved queries, aliases, and context assembly hints",
    "question": "asked questions with answers and correctness (quizzes, probes, learning)",
    "decision": "decisions with context, options, choice, and rationale",
    "quiz": "a graded quiz batch: score, topic, weak areas, and linked questions",
}

# Types with dedicated constructors (create_question/decision/quiz) rather than
# free-form save().
RECORD_TYPES = {"question", "decision", "quiz"}
