# Skill Cooperation — Recording Questions & Decisions

Other skills (learning, quiz, probe, teach, review, planning, coding) record
into the memory workspace through two structured record types. This is the
contract any skill follows so its activity becomes durable, linked memory.

## When to record

| Skill activity | Record as | Tool |
|---|---|---|
| A quiz/probe/test question is asked | `question` | `log_question` |
| The learner answers (correct or wrong) | same `question` note, `correct` field | `log_question` |
| A decision is made (any skill, any project) | `decision` | `log_decision` |
| A milestone/learning emerges | `semantic` or `episodic` memory | `save` |

## Contract

Every record is a Markdown note in the vault with structured YAML frontmatter.
Records auto-link to the active session (from the session marker) — no manual
linking needed. Secrets are redacted before write.

### Question records — `memories/questions/`

Frontmatter: `type: question`, `question`, `answer`, `correct` (bool),
`topic`, `difficulty`, plus optional `entities`/`source_sessions`/`related`.

- MCP: `log_question(question, answer, correct, topic?, difficulty?)`
- CLI: `mnemosyne question --question "..." --answer "..." --correct true --topic databases --difficulty easy`

Correctness is a boolean; quizzes can record each question separately to keep
a per-question history, or record only the questions the learner got wrong
(topic + difficulty preserved) for spaced repetition.

### Decision records — `memories/decisions/`

Frontmatter: `type: decision`, `decision`, `context`, `options` (list),
`chosen`, `rationale`.

- MCP: `log_decision(decision, rationale, context?, options?, chosen?)`
- CLI: `mnemosyne decision --decision "Use Markdown" --context "..." --options A B C --chosen B --rationale "..."`

Decisions are `active` by default. When a decision is reversed or replaced,
`supersede` it (marks the old note `superseded`, links the new one with a
`supersedes` relation) — history is never silently overwritten.

## How learning skills integrate

The learn/quiz/probe/teach skills in this environment call the memory tools
through MCP (preferred) or CLI:

1. **Before a quiz/probe:** `recall(topic)` to see what the learner already
   knows (`question` records with `topic` filter; `semantic` records for
   established facts).
2. **During:** each question asked → `log_question`; each decision made →
   `log_decision`.
3. **After:** weak areas are queryable — `recall --type question topic=X`
   surfaces past misses so later sessions can re-test them.

## Recall

All records are retrievable with the standard tools:

```bash
mnemosyne recall --vault C:/Memory "database atomicity"          # exact + semantic
mnemosyne recall --vault C:/Memory --type question "databases"   # past quiz questions
mnemosyne recall --vault C:/Memory --type decision "Markdown"    # past decisions
```

`recall --type decision` is a ready-made decision log; `recall --type question
--topic X` is a ready-made spaced-repetition deck.

## Compatibility

- `doctor` and `review` treat question/decision records like any memory
  (orphan detection, broken-link checks, supersession history).
- `index` includes them in the disposable search index.
- Obsidian Graph View shows them linked to sessions/entities like all other
  memories.
