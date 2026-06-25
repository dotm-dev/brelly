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
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
        name = data.get("name") or p.stem
        results.append((name, p))
    return results


def build_run_config(source: Path, skip: set[str], dest: Path) -> None:
    """Write a copy of source config with skip_steps replaced by skip."""
    data = json.loads(source.read_text())
    data["skip_steps"] = sorted(skip)
    dest.write_text(json.dumps(data, indent=2))


def run_subprocess(
    cmd: list[str],
    out_queue: "queue.Queue[str | None]",
) -> None:
    """Run cmd in a background thread, put each output line into out_queue. Puts None when done."""
    def _target() -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(PROJECT_ROOT),
            )
            if proc.stdout is None:
                raise RuntimeError("Popen stdout is None — unexpected")
            for line in proc.stdout:
                out_queue.put(line.rstrip("\n"))
            proc.wait()
            if proc.returncode != 0:
                out_queue.put(f"✗ process exited with code {proc.returncode}")
            out_queue.put(None)  # sentinel: done
        except Exception as exc:
            out_queue.put(f"ERROR: {exc}")
            out_queue.put(None)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
