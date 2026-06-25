# pipeline/app.py
"""Brelly pipeline desktop runner."""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PIPELINE_DIR = Path(__file__).parent
CONFIG_DIR = PIPELINE_DIR / "config"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"

STEPS = [
    "download",
    "reproject",
    "terrain",
    "roads",
    "buildings",
    "vegetation",
    "road graph",
    "manifest",
    "compress",
]


def scan_configs(config_dir: Path) -> list[tuple[str, Path]]:
    """Return [(display_name, path), ...] sorted by display name, excluding example.json."""
    results = []
    for p in sorted(config_dir.glob("*.json")):
        if p.stem == "example":
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            data = {}
        name = data.get("name") or p.stem
        results.append((name, p))
    return results


def build_run_config(source: Path, skip: set[str], dest: Path) -> None:
    """Write a copy of source config with skip_steps replaced by skip."""
    data = json.loads(source.read_text())
    data["skip_steps"] = sorted(skip)
    dest.write_text(json.dumps(data, indent=2))
