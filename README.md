# eqt

A graphic equalizer for the terminal, built on top of
[EasyEffects](https://github.com/wwmm/easyeffects). Live 10-band bars,
arrow-key adjustment, named presets, and per-device autoloading.

## Features

- Live 10-band graphic equalizer (32 Hz – 16 kHz), rendered as vertical
  bars with a centered 0 dB baseline — positive gain fills upward,
  negative gain fills downward
- Fine (±0.5 dB) and coarse (±3 dB) adjustment, per-band and global reset
- Save and load named presets
- Per-device autoload: assign a preset to a specific output device using
  EasyEffects' own autoload mechanism, so it applies automatically
  whenever that device becomes active
- Changes apply live; no need to leave the equalizer to hear the result

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
| `s` | Save preset |
| `l` | Load preset |
| `g` | Assign current preset to a device (autoload) |
| `q` | Quit |

## Requirements

- Linux with PipeWire and [EasyEffects](https://github.com/wwmm/easyeffects) installed
- Python 3.10+
- `python-textual`

```bash
pip install textual
```

`eqt` starts EasyEffects in service mode automatically if it isn't
already running.

## Installation

```bash
git clone https://github.com/EPHAK/eqt.git
ln -s "$(pwd)/eqt/eqt" ~/.local/bin/eqt
```

Ensure `~/.local/bin` is on your `PATH`.

## How it works

`eqt` writes and loads standard EasyEffects preset files
(`~/.local/share/easyeffects/output/<name>.json`) and applies them via
`easyeffects --load-preset`. Per-device assignment writes to
EasyEffects' own autoload directory
(`~/.local/share/easyeffects/autoload/output/`), which EasyEffects
reads natively — `eqt` does not reimplement audio routing or profile
switching itself.

Presets only specify frequency and gain per band; filter type, mode,
slope, and other parameters fall back to EasyEffects' own defaults
(Bell filter, standard IIR mode).

## License

MIT
