"""Startup guard: eqt is a front-end, and says so when the backend is absent.

Failing after Textual has taken over the terminal paints a traceback over
a half-drawn UI and still exits 0, so the check belongs in main().
"""

from __future__ import annotations

import pytest

from eqt_tui import app as app_module
from eqt_tui import presets


def test_easyeffects_installed_follows_path(monkeypatch):
    monkeypatch.setattr(presets.shutil, "which", lambda name: None)
    assert presets.easyeffects_installed() is False
    monkeypatch.setattr(presets.shutil, "which", lambda name: "/usr/bin/easyeffects")
    assert presets.easyeffects_installed() is True


def test_ensure_service_running_is_a_noop_without_the_binary(monkeypatch):
    """It must not reach subprocess and raise FileNotFoundError."""
    monkeypatch.setattr(presets, "easyeffects_installed", lambda: False)

    def fail(*a, **k):
        raise AssertionError("should not have run a subprocess")

    monkeypatch.setattr(presets.subprocess, "run", fail)
    monkeypatch.setattr(presets.subprocess, "Popen", fail)
    presets.ensure_service_running()


def test_main_exits_nonzero_without_easyeffects(monkeypatch, capsys):
    monkeypatch.setattr(app_module.presets, "easyeffects_installed", lambda: False)
    monkeypatch.setattr("sys.argv", ["eqt"])

    started = []
    monkeypatch.setattr(app_module.EqtApp, "run", lambda self: started.append(True))

    with pytest.raises(SystemExit) as exc:
        app_module.main()
    assert exc.value.code == 1
    assert started == [], "the TUI must not start"
    assert "EasyEffects is not installed" in capsys.readouterr().err


def test_main_starts_the_tui_when_easyeffects_is_present(monkeypatch):
    monkeypatch.setattr(app_module.presets, "easyeffects_installed", lambda: True)
    monkeypatch.setattr("sys.argv", ["eqt"])
    started = []
    monkeypatch.setattr(app_module.EqtApp, "run", lambda self: started.append(True))
    app_module.main()
    assert started == [True]
