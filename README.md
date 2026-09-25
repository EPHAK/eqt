# eqt

A graphic equalizer for the terminal, built on top of
[EasyEffects](https://github.com/wwmm/easyeffects). Live 10-band bars,
arrow-key adjustment, named presets, and per-device autoloading.

## Features

- Live 10-band graphic equalizer (32 Hz – 16 kHz), rendered as vertical
  bars with a centered 0 dB baseline: positive gain fills upward,
  negative gain fills downward
- Fine (±0.5 dB) and coarse (±3 dB) adjustment, per-band and global reset
- Save, load, and delete named presets. Live editing never overwrites a
  saved preset; only the Save action does, and only when you name it,
  so you can freely experiment on top of a loaded preset and reload it
  to discard changes, the same way a game save works
- Per-device autoload: assign a preset to a specific output device using
  EasyEffects' own autoload mechanism, so it applies automatically
  whenever that device becomes active
- Changes apply live; no need to leave the equalizer to hear the result
- The working state persists across restarts, independent of any named
  preset, so unsaved edits are never lost between sessions

## Usage

```bash
eqt
```

| Key | Action |
|---|---|
| `←` / `→` | Select band |
| `↑` / `↓` | Adjust gain ±0.5 dB |
| `PgUp` / `PgDn` | Adjust gain ±3 dB |
| `0` | Reset selected band |
| `Shift+R` | Reset all bands |
| `s` | Save preset (name defaults to the currently loaded preset, selected for easy overwrite or replacement) |
| `l` | Open the preset list (`Enter` to load, `d` to delete the highlighted preset) |
| `g` | Assign current preset to a device (autoload) |
| `q` | Quit |

## Requirements

- Linux with PipeWire and [EasyEffects](https://github.com/wwmm/easyeffects) installed
- Python 3.10+

The `textual` dependency is installed automatically by the commands
below. `eqt` starts EasyEffects in service mode automatically if it
isn't already running.

## Installation

```bash
pipx install git+https://github.com/EPHAK/eqt.git
```

Or from a clone, for development:

```bash
git clone https://github.com/EPHAK/eqt.git
cd eqt
pip install -e ".[dev]"
```

Either way this puts an `eqt` command on your `PATH`.

If you install with `pip` rather than `pipx` on an older distribution,
upgrade `pip` first (`python3 -m pip install --upgrade pip`). Versions
before roughly 23.x build this package as an empty `UNKNOWN` wheel and
still report success, leaving nothing installed.


## How it works

`eqt` writes and loads standard EasyEffects preset files
(`~/.local/share/easyeffects/output/<name>.json`, or under
`$XDG_DATA_HOME` when set) and applies them via
`easyeffects --load-preset`. Per-device assignment writes to
EasyEffects' own autoload directory
(`~/.local/share/easyeffects/autoload/output/`), which EasyEffects
reads natively. `eqt` does not reimplement audio routing or profile
switching itself.

Live editing always applies through a dedicated internal preset
(`_eqt_live`), never a named one. Loading a saved preset copies its
values into this live slot as a starting point; only Save writes to a
named preset file. This keeps saved presets stable regardless of how
much further experimentation happens after loading them.

Presets only specify frequency and gain per band; filter type, mode,
slope, and other parameters fall back to EasyEffects' own defaults
(Bell filter, standard IIR mode).

## License

[MIT](LICENSE)
