from __future__ import annotations

from rich.console import RenderableType
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget
from textual.reactive import reactive

from .presets import GAIN_MIN, GAIN_MAX

BAR_CHARS = " ▁▂▃▄▅▆▇█"  # 0..8 eighths, for sub-cell precision


class GraphicEqualizer(Widget):
    """
    A live, keyboard-driven graphic equalizer: one vertical bar per band,
    a center 0dB line, and a highlighted cursor on the selected band.
    Pure Textual/Rich rendering -- no external plotting library.
    """

    can_focus = True
    selected: reactive[int] = reactive(0)

    def __init__(self, bands, **kwargs):
        super().__init__(**kwargs)
        self.bands = bands  # list[Band], shared/mutated by the App

    def render_line(self, y: int) -> Strip:
        height = self.size.height
        if height <= 0:
            return Strip.blank(self.size.width)

        bar_width = 7
        segments: list[Segment] = []
        zero_row = height // 2  # row index for the 0dB baseline

        for i, band in enumerate(self.bands):
            is_selected = i == self.selected
            frac = (band.gain - GAIN_MIN) / (GAIN_MAX - GAIN_MIN)  # 0..1
            # bar height in eighths of a cell, symmetric around the middle row
            total_eighths = int(round(frac * height * 8)) - height * 4
            filled_rows_from_bottom = total_eighths / 8.0

            row_from_bottom = height - 1 - y
            cell_value = filled_rows_from_bottom - row_from_bottom  # how "full" this cell is, can be negative/large

            base_color = "cyan" if not is_selected else "yellow"
            if band.gain == 0:
                base_color = "grey50" if not is_selected else "yellow"
            elif band.gain > 0:
                base_color = "green" if not is_selected else "yellow"
            else:
                base_color = "red" if not is_selected else "yellow"

            style = Style(color=base_color, bold=is_selected)

            if cell_value >= 1:
                ch = BAR_CHARS[8]
            elif cell_value <= 0:
                ch = " "
            else:
                idx = max(0, min(8, int(round(cell_value * 8))))
                ch = BAR_CHARS[idx]

            # 0dB baseline marker when the bar itself doesn't reach here
            if y == zero_row and ch == " ":
                ch = "─"
                style = Style(color="grey37")

            bar_str = ch * (bar_width - 1) + " "
            segments.append(Segment(bar_str, style))

        return Strip(segments).adjust_cell_length(self.size.width)

    def move_selection(self, delta: int) -> None:
        self.selected = max(0, min(len(self.bands) - 1, self.selected + delta))
        self.refresh()

    def adjust_gain(self, delta: float) -> None:
        b = self.bands[self.selected]
        b.gain = max(GAIN_MIN, min(GAIN_MAX, round(b.gain + delta, 1)))
        self.refresh()

    def reset_band(self) -> None:
        self.bands[self.selected].gain = 0.0
        self.refresh()

    def reset_all(self) -> None:
        for b in self.bands:
            b.gain = 0.0
        self.refresh()
