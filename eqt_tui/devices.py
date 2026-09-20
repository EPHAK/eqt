"""
Output device listing + EasyEffects per-device autoload management.

Uses EasyEffects' own autoload mechanism: a JSON file per device at
$EE_DATA/autoload/<channel>/<device_node>:<port_name>.json with
device / device-description / device-profile / preset-name fields.
EasyEffects applies the matching preset automatically whenever that
device becomes active.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .presets import EE_DATA


@dataclass
class OutputDevice:
    name: str
    description: str
    active_port: str | None


def list_output_devices() -> list[OutputDevice]:
    result = subprocess.run(["pactl", "-f", "json", "list", "sinks"], capture_output=True, text=True, timeout=10)
    result.check_returncode()
    data = json.loads(result.stdout)
    devices = []
    for s in data:
        if s["name"] == "easyeffects_sink":
            continue  # EasyEffects' own virtual sink, not a real output device
        devices.append(OutputDevice(name=s["name"], description=s.get("description", s["name"]), active_port=s.get("active_port")))
    return devices


def _safe_filename(device_node: str, port: str | None) -> str:
    key = f"{device_node}:{port}" if port else device_node
    return re.sub(r"[^A-Za-z0-9_.:\[\] -]", "_", key) + ".json"


def autoload_dir(channel: str = "output") -> Path:
    d = EE_DATA / "autoload" / channel
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_autoload(device: OutputDevice, preset_name: str, channel: str = "output") -> Path:
    path = autoload_dir(channel) / _safe_filename(device.name, device.active_port)
    data = {
        "device": device.name,
        "device-description": device.description,
        "device-profile": device.active_port or "",
        "preset-name": preset_name,
    }
    path.write_text(json.dumps(data, indent=2))
    return path


def clear_autoload(device: OutputDevice, channel: str = "output") -> None:
    path = autoload_dir(channel) / _safe_filename(device.name, device.active_port)
    if path.exists():
        path.unlink()


def get_autoload(device: OutputDevice, channel: str = "output") -> str | None:
    path = autoload_dir(channel) / _safe_filename(device.name, device.active_port)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text()).get("preset-name")
    except Exception:
        return None
