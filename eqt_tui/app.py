from __future__ import annotations

import asyncio

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, Input, Label, ListView, ListItem, Button

from . import presets
from . import devices
from .eq_widget import GraphicEqualizer
from .presets import DEFAULT_FREQUENCIES


def _freq_label(f: float) -> str:
    if f >= 1000:
        v = f / 1000
        return f"{v:g}k"
    return f"{f:g}"


class NameModal(ModalScreen[str | None]):
    def __init__(self, title: str):
        super().__init__()
        self.title_text = title

    def compose(self) -> ComposeResult:
        with Vertical(id="name-box"):
            yield Label(self.title_text)
            yield Input(id="name-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class PresetListModal(ModalScreen[str | None]):
    def __init__(self, names: list[str]):
        super().__init__()
        self.names = names

    def compose(self) -> ComposeResult:
        with Vertical(id="preset-list-box"):
            yield Label("Load preset (enter=load, d=delete, esc=cancel)")
            lv = ListView(id="preset-list")
            yield lv

    async def on_mount(self) -> None:
        lv = self.query_one(ListView)
        for n in self.names:
            item = ListItem(Label(n))
            item.preset_name = n
            await lv.append(item)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(getattr(event.item, "preset_name", None))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class DeviceListModal(ModalScreen[tuple | None]):
    """Pick an output device to assign the current preset to (per-device autoload)."""

    def __init__(self, devs: list[devices.OutputDevice]):
        super().__init__()
        self.devs = devs

    def compose(self) -> ComposeResult:
        with Vertical(id="device-list-box"):
            yield Label("Assign current preset to device (enter=set, c=clear autoload, esc=cancel)")
            yield ListView(id="device-list")

    async def on_mount(self) -> None:
        lv = self.query_one(ListView)
        for d in self.devs:
            current = devices.get_autoload(d)
            tag = f"  [dim](autoload: {current})[/dim]" if current else "  [dim](no autoload)[/dim]"
            item = ListItem(Label(d.description + tag))
            item.device = d
            await lv.append(item)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(("set", getattr(event.item, "device", None)))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "c":
            lv = self.query_one(ListView)
            item = lv.highlighted_child
            if item is not None:
                self.dismiss(("clear", getattr(item, "device", None)))


class EqtApp(App):
    CSS = """
    #name-box, #preset-list-box, #device-list-box {
        width: 60; height: auto; border: round $accent; padding: 1 2; background: $surface;
    }
    #preset-list, #device-list { height: 10; }
    NameModal, PresetListModal, DeviceListModal { align: center middle; }
    GraphicEqualizer { height: 1fr; min-height: 12; border: solid $accent; }
    #freq-row { height: 1; }
    #status-row { height: 1; padding: 0 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("left", "move_left", "◀"),
        Binding("right", "move_right", "▶"),
        Binding("up", "gain_up", "+0.5dB"),
        Binding("down", "gain_down", "-0.5dB"),
        Binding("pageup", "gain_up_coarse", "+3dB"),
        Binding("pagedown", "gain_down_coarse", "-3dB"),
        Binding("0", "reset_band", "Reset band"),
        # Terminals encode Shift on a printable letter as the uppercase
        # character itself ("R"), not a separate modifier, so this binds
        # to "R" rather than "shift+r".
        Binding("R", "reset_all", "Reset all"),
        Binding("s", "save_preset", "Save"),
        Binding("l", "load_preset", "Load"),
        Binding("g", "assign_device", "Per-device"),
    ]

    def __init__(self):
        super().__init__()
        self.bands = presets.default_bands()
        self.current_preset_name: str | None = None
        self._apply_timer = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield GraphicEqualizer(self.bands, id="eq")
        freq_labels = "".join(f"{_freq_label(f):^7}" for f in DEFAULT_FREQUENCIES)
        yield Static(freq_labels, id="freq-row")
        yield Static("", id="status-row")
        yield Static(
            "[dim]←/→ band  ↑/↓ ±0.5dB  PgUp/PgDn ±3dB  0 reset band  Shift+R reset all  "
            "s save  l load  g per-device[/dim]",
            id="hints",
        )
        yield Footer()

    async def on_mount(self) -> None:
        presets.ensure_service_running()
        self.update_status()

    def update_status(self) -> None:
        eq = self.query_one(GraphicEqualizer)
        band = self.bands[eq.selected]
        preset_label = self.current_preset_name or "(unsaved)"
        self.query_one("#status-row", Static).update(
            f"Band: {_freq_label(band.frequency)}Hz   Gain: {band.gain:+.1f} dB   Preset: {preset_label}"
        )

    @work(thread=True, exclusive=True, group="apply-live")
    def _apply_live_now(self) -> None:
        # Runs in a worker thread: applying a preset shells out to
        # `easyeffects --load-preset`, which takes on the order of 100ms.
        # Calling it directly on the event loop would block input handling
        # and rendering for that long on every single adjustment.
        name = self.current_preset_name or "_eqt_live"
        try:
            presets.save_preset(name, self.bands)
            presets.apply_preset_cli(name)
        except Exception as e:
            self.call_from_thread(self.notify, f"Apply failed: {e}", severity="error")

    def _schedule_apply(self) -> None:
        # Debounced: rapid key-repeat (holding an arrow key) would otherwise
        # queue a subprocess call per keystroke. Only the last adjustment
        # in a burst actually gets written/applied, ~120ms after input
        # goes quiet -- the visual bars still update on every keypress.
        if self._apply_timer is not None:
            self._apply_timer.stop()
        self._apply_timer = self.set_timer(0.12, self._apply_live_now)

    def action_move_left(self) -> None:
        self.query_one(GraphicEqualizer).move_selection(-1)
        self.update_status()

    def action_move_right(self) -> None:
        self.query_one(GraphicEqualizer).move_selection(1)
        self.update_status()

    def action_gain_up(self) -> None:
        self.query_one(GraphicEqualizer).adjust_gain(0.5)
        self.update_status()
        self._schedule_apply()

    def action_gain_down(self) -> None:
        self.query_one(GraphicEqualizer).adjust_gain(-0.5)
        self.update_status()
        self._schedule_apply()

    def action_gain_up_coarse(self) -> None:
        self.query_one(GraphicEqualizer).adjust_gain(3.0)
        self.update_status()
        self._schedule_apply()

    def action_gain_down_coarse(self) -> None:
        self.query_one(GraphicEqualizer).adjust_gain(-3.0)
        self.update_status()
        self._schedule_apply()

    def action_reset_band(self) -> None:
        self.query_one(GraphicEqualizer).reset_band()
        self.update_status()
        self._schedule_apply()

    def action_reset_all(self) -> None:
        self.query_one(GraphicEqualizer).reset_all()
        self.update_status()
        self._schedule_apply()

    @work
    async def action_save_preset(self) -> None:
        name = await self.push_screen_wait(NameModal("Save preset as:"))
        if not name:
            return
        await asyncio.to_thread(presets.save_preset, name, self.bands)
        await asyncio.to_thread(presets.apply_preset_cli, name)
        self.current_preset_name = name
        self.update_status()
        self.notify(f"Saved preset '{name}'")

    @work
    async def action_load_preset(self) -> None:
        names = await asyncio.to_thread(presets.list_presets)
        if not names:
            self.notify("No saved presets yet")
            return
        chosen = await self.push_screen_wait(PresetListModal(names))
        if not chosen:
            return
        loaded_bands = await asyncio.to_thread(presets.load_preset_from_file, chosen)
        self.bands.clear()
        self.bands.extend(loaded_bands)
        self.query_one(GraphicEqualizer).bands = self.bands
        self.query_one(GraphicEqualizer).refresh()
        self.current_preset_name = chosen
        self.update_status()
        await asyncio.to_thread(presets.apply_preset_cli, chosen)
        self.notify(f"Loaded preset '{chosen}'")

    @work
    async def action_assign_device(self) -> None:
        name = self.current_preset_name
        if not name:
            self.notify("Save the preset first (s) before assigning it to a device")
            return
        devs = await asyncio.to_thread(devices.list_output_devices)
        result = await self.push_screen_wait(DeviceListModal(devs))
        if not result:
            return
        action, device = result
        if device is None:
            return
        if action == "set":
            await asyncio.to_thread(devices.set_autoload, device, name)
            self.notify(f"'{name}' will now autoload when {device.description} is active")
        elif action == "clear":
            await asyncio.to_thread(devices.clear_autoload, device)
            self.notify(f"Cleared autoload for {device.description}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="eqt -- graphic equalizer TUI on EasyEffects (run with no arguments for the interactive UI)"
    )
    parser.parse_args()  # no real flags yet; this just makes -h/--help behave instead of launching the TUI
    EqtApp().run()


if __name__ == "__main__":
    main()
