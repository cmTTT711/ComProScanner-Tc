"""Offline test isolation without replacing whole dependency trees with mocks."""

import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


@pytest.fixture(autouse=True)
def offline_network(monkeypatch, request):
    if request.node.get_closest_marker("integration"):
        return
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Offline tests cannot open network connections")

    monkeypatch.setattr(socket.socket, "connect", denied)


@pytest.fixture
def share_scopus_api_key():
    return "dummy_scopus_api_key"


@pytest.fixture(autouse=True)
def isolate_runtime_files(tmp_path, monkeypatch):
    (tmp_path / "results/extracted_data/piezoelectric").mkdir(
        parents=True, exist_ok=True
    )
    monkeypatch.chdir(tmp_path)
