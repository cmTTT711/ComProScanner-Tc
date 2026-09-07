from comproscanner.cli.main import main


def test_presets_command_lists_tc(capsys):
    assert main(["presets"]) == 0
    assert "curie_temperature" in capsys.readouterr().out
