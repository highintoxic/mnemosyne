from obsidian_memory.config import VaultConfig
from obsidian_memory.maintenance import doctor, rebuild_index
from obsidian_memory.relations import RelationStore


def test_doctor_reports_broken_relation_target(tmp_path):
    VaultConfig.initialize(tmp_path)
    RelationStore(tmp_path).add("missing_source", "supports", "missing_target")
    report = doctor(tmp_path)
    assert report["broken_links"]


def test_rebuild_index_is_disposable(tmp_path):
    VaultConfig.initialize(tmp_path)
    index = rebuild_index(tmp_path)
    assert index.is_file()
    index.unlink()
    assert not index.exists()
