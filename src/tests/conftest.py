import pytest


@pytest.fixture(autouse=True)
def _no_shadow(monkeypatch):
    """the trained-router shadow thread must not run during tests (it would load weights and compete for the CPU)"""
    from omnipool import schatten
    monkeypatch.setattr(schatten, "modus", lambda: "off")


@pytest.fixture(autouse=True)
def _no_local_analyst(monkeypatch):
    """the local analyst (a llama-server process) must not start during tests unless a test turns it on"""
    from omnipool import analyst
    monkeypatch.setattr(analyst, "modus", lambda: "off")
