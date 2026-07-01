# pipeline/settings.py
"""Small local settings file (e.g. the remembered swissTLM3D path) shared
across New Map sessions. Lives at pipeline/config/.settings.json,
git-ignored, distinct from per-map config files."""
import json
from pathlib import Path

_DEFAULTS = {"tlm_path": ""}


def load_settings(settings_path: Path) -> dict:
    if not settings_path.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def save_settings(settings_path: Path, data: dict) -> None:
    settings_path.write_text(json.dumps(data, indent=2))
