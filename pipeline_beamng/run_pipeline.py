#!/usr/bin/env python3
# pipeline_beamng/run_pipeline.py
"""Orchestrator: exports a Brelly map config as a BeamNG level (terrain +
roads). Mirrors pipeline/run_pipeline.py's subprocess-per-step pattern —
numbered scripts are invoked as subprocesses, never imported directly."""
import subprocess
import sys
from pathlib import Path

STEPS = [
    ("terrain", "scripts/00_terrain.py"),
    ("roads",   "scripts/01_roads.py"),
    ("package", "scripts/02_package.py"),
]


def run(config_path: str) -> None:
    pipeline_dir = Path(__file__).parent

    for label, script in STEPS:
        print(f"  {label} ...", flush=True)
        result = subprocess.run(
            [sys.executable, str(pipeline_dir / script), config_path],
            check=False,
        )
        if result.returncode != 0:
            print(f"\n  x {label} failed (exit {result.returncode})\n")
            sys.exit(result.returncode)
        print(f"  {label} done")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    run(sys.argv[1])
