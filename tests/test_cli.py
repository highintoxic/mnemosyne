from obsidian_memory.cli import main


def test_cli_init_and_recall(tmp_path, capsys):
    assert main(["init", "--vault", str(tmp_path)]) == 0
    assert main(["save", "--vault", str(tmp_path), "--type", "semantic", "--title", "Local", "--body", "Works offline"]) == 0
    assert main(["recall", "--vault", str(tmp_path), "offline"]) == 0
    assert "Works offline" in capsys.readouterr().out
