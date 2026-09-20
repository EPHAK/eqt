import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eqt_tui.app import EqtApp
from eqt_tui.eq_widget import GraphicEqualizer


async def main():
    app = EqtApp()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        eq = app.query_one(GraphicEqualizer)
        print("initial selected band:", eq.selected, "gain:", app.bands[0].gain)

        await pilot.press("right")
        await pilot.press("right")
        print("after 2x right, selected:", eq.selected)

        await pilot.press("up")
        await pilot.press("up")
        await pilot.pause(0.3)
        print("after 2x up, band2 gain:", app.bands[2].gain)

        await pilot.press("pagedown")
        await pilot.pause(0.3)
        print("after pagedown, band2 gain:", app.bands[2].gain)

        await pilot.press("0")
        await pilot.pause(0.2)
        print("after reset, band2 gain:", app.bands[2].gain)

        # save preset flow
        await pilot.press("s")
        await pilot.pause()
        await pilot.press("t", "e", "s", "t", "p", "r", "e", "s", "e", "t")
        await pilot.press("enter")
        await pilot.pause(0.3)
        print("current_preset_name:", app.current_preset_name)

        import eqt_tui.presets as presets
        print("saved presets on disk:", presets.list_presets())
        print("--presets CLI sees it:", end=" ")


asyncio.run(main())
