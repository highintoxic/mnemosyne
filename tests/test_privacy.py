from mnemosyne.journal import Journal
from mnemosyne.config import VaultConfig
from mnemosyne.notes import read_note
from mnemosyne.privacy import is_ignored, redact_sensitive
from mnemosyne.relations import RelationStore
from mnemosyne.store import MemoryStore


def test_redacts_common_token():
    clean, findings = redact_sensitive("token=ghp_abcdefghijklmnopqrstuvwxyz123456")
    assert "ghp_" not in clean
    assert findings


def test_ignore_marker_blocks_capture():
    assert is_ignored("normal text\n<!-- memory:ignore -->\nsecret")


def test_journal_appends_jsonl(tmp_path):
    journal = Journal(tmp_path / ".memory/journal/events.jsonl")
    journal.append({"event": "saved", "id": "mem_1"})
    assert '"event": "saved"' in journal.path.read_text(encoding="utf-8")


def test_entity_and_relation_evidence_are_redacted(tmp_path):
    VaultConfig.initialize(tmp_path)
    store = MemoryStore(tmp_path)
    relations = RelationStore(tmp_path)
    entity = store.create_entity("project", "Private", {"description": "token=ghp_abcdefghijklmnopqrstuvwxyz123456"})
    target_mem = store.create_memory("semantic", "Target", "Body.", {})
    target_id = read_note(target_mem)[0]["id"]
    relation = relations.add(entity.stem, "related-to", target_id, "Bearer abcdefghijklmnopqrstuvwxyz")
    assert "ghp_" not in read_note(entity)[1]
    assert "Bearer abc" not in read_note(relation)[1]
