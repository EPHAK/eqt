import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eqt_tui import app as eqt_app
from eqt_tui import presets, devices
from eqt_tui.app import EqtApp
from eqt_tui.eq_widget import GraphicEqualizer


class EqtAppTest(unittest.IsolatedAsyncioTestCase):
    """
    Every test here runs against an isolated EE_DATA directory and mocks
    out apply_preset_cli/ensure_service_running -- nothing in this suite
    is allowed to touch the real ~/.local/share/easyeffects directory or
    the real running EasyEffects service. A prior, unisolated version of
    this file wrote a preset literally named "testpreset" straight into
    the real preset folder on every run.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        state_dir = self.tmp_path / "state"
        theme_file = state_dir / "theme"

        self._patches = [
            mock.patch.object(presets, "EE_DATA", self.tmp_path / "easyeffects"),
            mock.patch.object(devices, "EE_DATA", self.tmp_path / "easyeffects"),
            mock.patch.object(eqt_app, "STATE_DIR", state_dir),
            mock.patch.object(eqt_app, "THEME_FILE", theme_file),
            mock.patch.object(presets, "ensure_service_running"),
            mock.patch.object(presets, "apply_preset_cli"),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_band_navigation_and_gain_adjustment(self):
        app = EqtApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            eq = app.query_one(GraphicEqualizer)
            self.assertEqual(eq.selected, 0)
            self.assertEqual(app.bands[0].gain, 0.0)

            await pilot.press("right", "right")
            self.assertEqual(eq.selected, 2)

            await pilot.press("up", "up")
            await pilot.pause(0.3)
            self.assertEqual(app.bands[2].gain, 1.0)

            await pilot.press("pagedown")
            await pilot.pause(0.3)
            self.assertEqual(app.bands[2].gain, -2.0)

            await pilot.press("0")
            await pilot.pause(0.3)
            self.assertEqual(app.bands[2].gain, 0.0)

    async def test_save_then_list_preset(self):
        app = EqtApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right", "up", "up")
            await pilot.pause(0.3)

            await pilot.press("s")
            await pilot.pause()
            name_input = app.screen.query_one("Input")
            name_input.value = ""
            await pilot.pause()
            await pilot.press(*"my-real-preset")
            await pilot.press("enter")
            await pilot.pause(0.3)

            self.assertEqual(app.current_preset_name, "my-real-preset")
            self.assertIn("my-real-preset", presets.list_presets())
            # the internal live slot must never show up as a user-facing preset
            self.assertNotIn(presets.LIVE_PRESET_NAME, presets.list_presets())

    async def test_editing_after_load_does_not_overwrite_saved_preset(self):
        """Regression for the reported 'video game save' bug: loading a
        preset then tweaking it live must never change the saved file
        until Save is explicitly used again."""
        bands = presets.default_bands()
        bands[0].gain = 5.0
        presets.save_preset("baseline", bands)

        app = EqtApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause(0.2)
            # highlight and load "baseline" (only entry in the list)
            await pilot.press("enter")
            await pilot.pause(0.3)
            self.assertEqual(app.current_preset_name, "baseline")
            self.assertEqual(app.bands[0].gain, 5.0)

            # experiment live without saving
            await pilot.press("up", "up")
            await pilot.pause(0.3)
            self.assertEqual(app.bands[0].gain, 6.0)

            on_disk = presets.load_preset_from_file("baseline")
            self.assertEqual(on_disk[0].gain, 5.0, "live edit must not have touched the saved file")

    async def test_delete_preset_from_list(self):
        presets.save_preset("to-delete", presets.default_bands())
        self.assertIn("to-delete", presets.list_presets())

        app = EqtApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause(0.2)
            await pilot.press("d")
            await pilot.pause(0.3)

        self.assertNotIn("to-delete", presets.list_presets())

    async def test_live_state_persists_across_restart(self):
        app1 = EqtApp()
        async with app1.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right", "right", "right", "up")
            await pilot.pause(0.3)
            gain = app1.bands[3].gain

        app2 = EqtApp()
        async with app2.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app2.bands[3].gain, gain)

    async def test_theme_persists_across_restart(self):
        app1 = EqtApp()
        async with app1.run_test() as pilot:
            await pilot.pause()
            chosen = "nord" if "nord" in app1.available_themes else list(app1.available_themes)[2]
            app1.theme = chosen
            await pilot.pause()

        app2 = EqtApp()
        async with app2.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app2.theme, chosen)


if __name__ == "__main__":
    unittest.main()
