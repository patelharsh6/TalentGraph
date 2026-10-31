"""Step 4.3: threshold presets (precision / balanced / recall) and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml

ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = ROOT / "config" / "matching.yaml"

PresetName = Literal["precision", "balanced", "recall"]

DEFAULT_PRESETS: dict[str, float] = {
    "precision": 0.75,
    "balanced": 0.60,
    "recall": 0.45,
}


def load_presets(config_path: Path | str | None = None) -> dict[str, float]:
    """Load threshold presets from matching.yaml configuration."""
    path = Path(config_path or CONFIG_PATH)
    if not path.is_file():
        return dict(DEFAULT_PRESETS)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        presets = data.get("presets", {})
        return {
            "precision": float(presets.get("precision", DEFAULT_PRESETS["precision"])),
            "balanced": float(presets.get("balanced", DEFAULT_PRESETS["balanced"])),
            "recall": float(presets.get("recall", DEFAULT_PRESETS["recall"])),
        }
    except Exception:
        return dict(DEFAULT_PRESETS)


def resolve_threshold(
    preset_or_value: str | float | None = None,
    presets: dict[str, float] | None = None,
) -> tuple[float, str | None]:
    """Resolve threshold and preset name from either a preset string or numeric float.

    Returns:
        (threshold_value, preset_name_or_None)
    """
    active_presets = presets or load_presets()

    if preset_or_value is None:
        return active_presets["balanced"], "balanced"

    if isinstance(preset_or_value, (int, float)):
        val = float(preset_or_value)
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"Custom threshold must be between 0.0 and 1.0, got {val}")
        # Check if it exactly matches a preset
        for name, pval in active_presets.items():
            if abs(val - pval) < 1e-6:
                return val, name
        return val, None

    if isinstance(preset_or_value, str):
        preset_key = preset_or_value.lower().strip()
        if preset_key in active_presets:
            return active_presets[preset_key], preset_key
        # Check if numeric string
        try:
            val = float(preset_key)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"Custom threshold must be between 0.0 and 1.0, got {val}")
            return val, None
        except ValueError:
            valid_names = ", ".join(active_presets.keys())
            msg = (
                f"Unknown threshold preset '{preset_or_value}'. "
                f"Must be one of ({valid_names}) or a float in [0.0, 1.0]."
            )
            raise ValueError(msg) from None

    raise TypeError(f"Invalid threshold argument type: {type(preset_or_value)}")
