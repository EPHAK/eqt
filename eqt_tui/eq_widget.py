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
        # 0dB sits at the vertical center of the widget: positive gain
        # fills upward from it, negative gain fills downward. This is a
        # bipolar bar, not a bottom-up one -- gain is drawn relative to
        # 0dB, not relative to GAIN_MIN.
        center = height / 2.0

        row_from_bottom = height - 1 - y
        row_lo, row_hi = float(row_from_bottom), float(row_from_bottom + 1)

        for i, band in enumerate(self.bands):
            is_selected = i == self.selected
            gain = band.gain

            if gain >= 0:
                extent = (gain / GAIN_MAX) * center if GAIN_MAX else 0.0
                fill_lo, fill_hi = center, center + extent
            else:
                extent = (-gain / -GAIN_MIN) * center if GAIN_MIN else 0.0
                fill_lo, fill_hi = center - extent, center

            overlap = max(0.0, min(row_hi, fill_hi) - max(row_lo, fill_lo))
            cell_value = max(0.0, min(1.0, overlap))

            if gain == 0:
                base_color = "grey50"
            elif gain > 0:
                base_color = "green"
            else:
                base_color = "red"
            style = Style(color=("yellow" if is_selected else base_color), bold=is_selected)

            if cell_value >= 1:
                ch = BAR_CHARS[8]
            elif cell_value <= 0:
                ch = " "
            else:
                idx = max(1, min(8, int(round(cell_value * 8))))
                ch = BAR_CHARS[idx]

            # 0dB baseline marker on whichever row actually contains the
            # center line, so it's visible even when nothing is filled.
            if row_lo <= center < row_hi and ch == " ":
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
