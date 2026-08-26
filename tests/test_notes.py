from mnemosyne.config import VaultConfig
from mnemosyne.notes import read_note, write_note


def test_initialize_creates_default_layout(tmp_path):
    config = VaultConfig.initialize(tmp_path)
    assert (tmp_path / "memories/semantic").is_dir()
    assert (tmp_path / ".memory/config.json").is_file()
    assert config.schema_version == 1


def test_note_round_trip_uses_frontmatter(tmp_path):
    path = tmp_path / "note.md"
    write_note(path, {"id": "mem_test", "type": "semantic", "confidence": 0.8}, "A claim.")
    metadata, body = read_note(path)
    assert metadata["id"] == "mem_test"
    assert body == "A claim."


def test_initialize_does_not_replace_existing_file(tmp_path):
    welcome = tmp_path / "Welcome.md"
    welcome.write_text("keep", encoding="utf-8")
    VaultConfig.initialize(tmp_path)
    assert welcome.read_text(encoding="utf-8") == "keep"
