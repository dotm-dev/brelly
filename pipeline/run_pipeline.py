#!/usr/bin/env python3
# pipeline/run_pipeline.py
"""Orchestrator: runs all 8 pipeline steps in sequence for a given config."""
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = [
    ("download",    "scripts/00_download.py"),
    ("reproject",   "scripts/01_reproject.py"),
    ("terrain",     "scripts/02_terrain.py"),
    ("roads",       "scripts/03_roads.py"),
    ("buildings",   "scripts/04_buildings.py"),
    ("vegetation",  "scripts/05_vegetation.py"),
    ("road graph",  "scripts/06_road_graph.py"),
    ("manifest",    "scripts/07_manifest.py"),
    ("compress",    "scripts/08_compress.py"),
]

WIDTH = 52


def _bar(pct: int, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def run(config_path: str) -> None:
    pipeline_dir = Path(__file__).parent
    total = len(SCRIPTS)
    timings: list[tuple[str, float]] = []
    overall_start = time.monotonic()

    cfg = __import__("json").load(open(config_path))
    map_name = cfg.get("displayName") or cfg.get("name") or Path(config_path).stem
    print(f"\n  Map pipeline  ·  {map_name}")
    print("  " + "─" * WIDTH)

    skip = set(cfg.get("skip_steps", []))

    for idx, (label, script) in enumerate(SCRIPTS, 1):
        pct = int((idx - 1) / total * 100)

        if label in skip:
            print(f"  {_bar(100)}  {label}  (skipped)")
            continue

        print(f"  {_bar(pct)}  {label} …", flush=True)

        script_path = pipeline_dir / script
        t0 = time.monotonic()
        result = subprocess.run(
            [sys.executable, str(script_path), config_path],
            check=False,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PIPELINE_QUIET": "1"},
        )
        elapsed = time.monotonic() - t0
        timings.append((label, elapsed))

        if result.returncode != 0:
            print(f"\n  ✗ {label} failed (exit {result.returncode})\n")
            if result.stdout.strip():
                print(result.stdout)
            if result.stderr.strip():
                print(result.stderr)
            sys.exit(result.returncode)

        # overwrite the progress line with the completed step
        print(f"\033[1A\033[2K  {_bar(100)}  {label}  ({elapsed:.1f}s)")

    total_elapsed = time.monotonic() - overall_start
    print("  " + "─" * WIDTH)
    print(f"  Done in {total_elapsed:.1f}s\n")

    # per-step timing summary
    slowest = sorted(timings, key=lambda t: t[1], reverse=True)[:3]
    print("  Slowest steps:")
    for name, t in slowest:
        print(f"    {name:<14}  {t:.1f}s")
    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    run(sys.argv[1])
