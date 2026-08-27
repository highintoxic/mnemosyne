from mnemosyne.config import VaultConfig
from mnemosyne.maintenance import doctor
from mnemosyne.relations import RelationStore


def test_doctor_reports_broken_relation_target(tmp_path):
    VaultConfig.initialize(tmp_path)
    RelationStore(tmp_path).add("missing_source", "supports", "missing_target")
    report = doctor(tmp_path)
    assert report["broken_links"]



def test_malformed_note_is_still_a_valid_link_target(tmp_path):
    """A file on disk resolves in Obsidian even if its frontmatter is broken,
    so doctor reports it once (malformed), not twice (malformed + broken_link)."""
    VaultConfig.initialize(tmp_path)
    broken = tmp_path / "memories" / "semantic" / "broken.md"
    broken.write_text("no frontmatter here", encoding="utf-8")
    RelationStore(tmp_path).add("broken", "related-to", "also-missing")
    report = doctor(tmp_path)
    assert any("broken.md" in item for item in report["malformed"])
    assert not any("-> broken" in item for item in report["broken_links"])
    assert any("-> also-missing" in item for item in report["broken_links"])
