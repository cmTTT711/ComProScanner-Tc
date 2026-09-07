import pytest

from comproscanner.cli.main import main


def test_extract_never_calls_external_models_without_execute_flag():
    with pytest.raises(SystemExit, match="External model calls are disabled"):
        main(["extract", "--run-id", "tc_test"])


@pytest.mark.parametrize("command", ["discover", "acquire-oa"])
def test_network_commands_require_explicit_execution(command):
    arguments = (
        [command, "--query", "tc", "--start-year", "2020", "--end-year", "2026"]
        if command == "discover"
        else [command, "--shortlist", "shortlist.csv"]
    )
    with pytest.raises(SystemExit, match="Network access is disabled"):
        main(arguments)
