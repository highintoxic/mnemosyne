from obsidian_memory.cli import main
from obsidian_memory.maintenance import doctor, rebuild_index
from obsidian_memory.relations import RelationStore
from obsidian_memory.retrieval import Retriever
from obsidian_memory.sessions import SessionStore
from obsidian_memory.store import MemoryStore


def test_complete_offline_workflow(tmp_path):
    assert main(["init", "--vault", str(tmp_path)]) == 0
    store = MemoryStore(tmp_path)
    project = store.create_entity("project", "Memory Workspace", {})
    memory = store.create_memory("semantic", "Canonical", "Markdown is canonical and local.", {"entities": [project.stem]})
    session = SessionStore(tmp_path).start(project.stem, None, "claude")
    SessionStore(tmp_path).finalize(session.stem, {"goals": ["remember"], "work": ["captured"], "decisions": ["local"], "discoveries": [], "unresolved": [], "follow_ups": []})
    RelationStore(tmp_path).add(session.stem, "derived-from", memory.stem)
    assert Retriever(tmp_path).search("canonical")
    assert rebuild_index(tmp_path).exists()
    report = doctor(tmp_path)
    assert set(report) >= {"malformed", "duplicate_ids", "broken_links", "orphans", "invalid_statuses", "contradictions", "stale"}
