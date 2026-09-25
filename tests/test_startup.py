"""Startup and environment failures.

eqt is a front-end for EasyEffects and reads devices through `pactl`.
Neither is guaranteed to be present, and failing after Textual has taken
over the terminal paints a traceback over a half-drawn UI -- in the
missing-EasyEffects case it also used to exit 0, so nothing could detect
it.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eqt_tui import app as eqt_app
from eqt_tui import devices, presets
from eqt_tui.app import EqtApp


class EasyEffectsDetectionTest(unittest.TestCase):
    def test_installed_follows_path(self):
        with mock.patch.object(presets.shutil, "which", return_value=None):
            self.assertFalse(presets.easyeffects_installed())
        with mock.patch.object(presets.shutil, "which", return_value="/usr/bin/easyeffects"):
            self.assertTrue(presets.easyeffects_installed())

    def test_ensure_service_running_is_a_noop_without_the_binary(self):
        """It must not reach subprocess and raise FileNotFoundError."""
        with mock.patch.object(presets, "easyeffects_installed", return_value=False), \
             mock.patch.object(presets.subprocess, "run", side_effect=AssertionError("ran pgrep")), \
             mock.patch.object(presets.subprocess, "Popen", side_effect=AssertionError("ran easyeffects")):
            presets.ensure_service_running()


class MainGuardTest(unittest.TestCase):
    def test_exits_nonzero_without_easyeffects(self):
        with mock.patch.object(eqt_app.presets, "easyeffects_installed", return_value=False), \
             mock.patch.object(sys, "argv", ["eqt"]), \
             mock.patch.object(EqtApp, "run") as run, \
             mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit) as caught:
                eqt_app.main()
        self.assertEqual(caught.exception.code, 1)
        run.assert_not_called()

    def test_starts_the_tui_when_easyeffects_is_present(self):
        with mock.patch.object(eqt_app.presets, "easyeffects_installed", return_value=True), \
             mock.patch.object(sys, "argv", ["eqt"]), \
             mock.patch.object(EqtApp, "run") as run:
            eqt_app.main()
        run.assert_called_once()


class DeviceListingFailureTest(unittest.IsolatedAsyncioTestCase):
    """Pressing `g` must survive a machine with no reachable sound server.

    Isolated the same way as test_app.py: nothing here may touch the real
    ~/.local/share/easyeffects directory or the real running service.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        self._patches = [
            mock.patch.object(presets, "EE_DATA", tmp_path / "easyeffects"),
            mock.patch.object(devices, "EE_DATA", tmp_path / "easyeffects"),
            mock.patch.object(eqt_app, "STATE_DIR", tmp_path / "state"),
            mock.patch.object(eqt_app, "THEME_FILE", tmp_path / "state" / "theme"),
            mock.patch.object(presets, "ensure_service_running"),
            mock.patch.object(presets, "apply_preset_cli"),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    async def _run_assign(self, **patched):
        app = EqtApp()
        notices = []
        with mock.patch.object(devices, "list_output_devices", **patched), \
             mock.patch.object(EqtApp, "notify", lambda self, msg, **kw: notices.append(msg)):
            async with app.run_test() as pilot:
                await pilot.pause()
                app.current_preset_name = "something"
                # @work-decorated, so the call returns a Worker, not a coroutine.
                await app.action_assign_device().wait()
                await pilot.pause()
        return notices

    async def _notices_for(self, error):
        return await self._run_assign(side_effect=error)

    async def test_pactl_exiting_nonzero_is_reported(self):
        error = subprocess.CalledProcessError(1, ["pactl", "-f", "json", "list", "sinks"])
        notices = await self._notices_for(error)
        self.assertTrue(
            any("could not list output devices" in m for m in notices), notices
        )

    async def test_missing_pactl_is_reported(self):
        error = FileNotFoundError(2, "No such file or directory", "pactl")
        notices = await self._notices_for(error)
        self.assertTrue(any("pactl not found" in m for m in notices), notices)

    async def test_no_devices_found_is_reported(self):
        notices = await self._run_assign(return_value=[])
        self.assertTrue(any("no output devices" in m for m in notices), notices)


if __name__ == "__main__":
    unittest.main()
