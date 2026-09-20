"""
EasyEffects preset (equalizer) file management, targeting the Qt (v8+)
preset schema as implemented in src/equalizer_preset.cpp and
src/presets_manager.cpp upstream (wwmm/easyeffects). Older community
preset examples use a different schema in places -- notably bare plugin
names in plugins_order rather than "<plugin>#<instance>" -- and are not
compatible with this format.

Schema notes:
  - Presets live at ~/.local/share/easyeffects/<channel>/<name>.json,
    where channel is "output" or "input".
  - Top-level shape: json[channel]["blocklist"], json[channel]["plugins_order"]
    (a list of "<plugin>#<instance>" strings), and json[channel][instance_name]
    holding that plugin's own settings.
  - Per equalizer_preset.cpp's `load_channel`, any band field absent from
    the JSON falls back to EasyEffects' own default for that field, so a
    preset only needs to specify "frequency" and "gain" per band;
    type/mode/slope/width/mute/solo may be omitted and default to a Bell
    filter, standard IIR mode, and x1 slope.
  - `load` always loads both "left" and "right" regardless of
    split-channels, so both must be present with equal values for a
    normal (non-split) stereo EQ.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

EE_DATA = Path.home() / ".local" / "share" / "easyeffects"

# Classic 10-band graphic EQ layout (32Hz-16kHz, one octave-ish spacing).
DEFAULT_FREQUENCIES = [32.0, 64.0, 128.0, 256.0, 512.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]
NUM_BANDS = len(DEFAULT_FREQUENCIES)
GAIN_MIN, GAIN_MAX = -24.0, 24.0

EQUALIZER_INSTANCE = "equalizer#0"


@dataclass
class Band:
    frequency: float
    gain: float = 0.0


def default_bands() -> list[Band]:
    return [Band(frequency=f, gain=0.0) for f in DEFAULT_FREQUENCIES]


def _channel_json(bands: list[Band]) -> dict:
    out = {}
    for i, b in enumerate(bands):
        out[f"band{i}"] = {"frequency": b.frequency, "gain": b.gain}
    return out


def build_preset_json(bands: list[Band], input_gain: float = 0.0, output_gain: float = 0.0) -> dict:
    channel_json = _channel_json(bands)
    return {
        "blocklist": [],
        "plugins_order": [EQUALIZER_INSTANCE],
        EQUALIZER_INSTANCE: {
            "bypass": False,
            "input-gain": input_gain,
            "output-gain": output_gain,
            "num-bands": len(bands),
            "split-channels": False,
            "left": channel_json,
            "right": channel_json,
        },
    }


def preset_dir(channel: str = "output") -> Path:
    d = EE_DATA / channel
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_preset(name: str, bands: list[Band], channel: str = "output",
                 input_gain: float = 0.0, output_gain: float = 0.0) -> Path:
    path = preset_dir(channel) / f"{name}.json"
    data = {channel: build_preset_json(bands, input_gain, output_gain)}
    path.write_text(json.dumps(data, indent=2))
    return path


def load_preset_from_file(name: str, channel: str = "output") -> list[Band]:
    path = preset_dir(channel) / f"{name}.json"
    data = json.loads(path.read_text())
    eq = data[channel][EQUALIZER_INSTANCE]
    n = eq.get("num-bands", NUM_BANDS)
    left = eq.get("left", {})
    bands = []
    for i in range(n):
        b = left.get(f"band{i}", {})
        bands.append(Band(frequency=b.get("frequency", DEFAULT_FREQUENCIES[i] if i < len(DEFAULT_FREQUENCIES) else 0.0),
                           gain=b.get("gain", 0.0)))
    return bands


def list_presets(channel: str = "output") -> list[str]:
    d = preset_dir(channel)
    return sorted(p.stem for p in d.glob("*.json"))


def delete_preset(name: str, channel: str = "output") -> None:
    path = preset_dir(channel) / f"{name}.json"
    if path.exists():
        path.unlink()


def apply_preset_cli(name: str) -> None:
    """Tell the running EasyEffects service to load this preset now."""
    result = subprocess.run(
        ["easyeffects", "--load-preset", name],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"easyeffects --load-preset failed: {result.stderr.strip() or result.stdout.strip()}")


def ensure_service_running() -> None:
    """Start EasyEffects headless if it isn't already running."""
    check = subprocess.run(["pgrep", "-f", "easyeffects.*service-mode"], capture_output=True)
    if check.returncode != 0:
        subprocess.Popen(
            ["easyeffects", "--service-mode"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
