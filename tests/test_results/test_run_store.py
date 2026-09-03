import json

import pytest

from comproscanner.results import RunStore


def test_run_store_creates_stable_layout_and_atomic_json(tmp_path):
    store = RunStore(tmp_path, "tc_test")
    store.initialize()
    path = store.write_json("papers/paper_001.json", {"status": "COMPLETED"})
    assert path == tmp_path.resolve() / "runs" / "tc_test" / "papers" / "paper_001.json"
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "COMPLETED"
    assert store.evidence_dir.is_dir()


def test_run_store_refuses_path_escape(tmp_path):
    store = RunStore(tmp_path, "tc_test")
    with pytest.raises(ValueError, match="inside"):
        store.write_json("../../gold/do_not_overwrite.json", {})


def test_run_id_cannot_be_a_path(tmp_path):
    with pytest.raises(ValueError, match="path separators"):
        RunStore(tmp_path, "runs/tc")
