#!/usr/bin/env python3
# pipeline/scripts/07_manifest.py
"""Assemble manifest.json from config and pipeline outputs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.io import read_json, write_json, output_dir
from scripts.manifest import build_manifest


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    out_dir = output_dir(config_dict)
    lod_available = (out_dir / "terrain_lod1.glb").exists() and (out_dir / "terrain_lod2.glb").exists()
    manifest = build_manifest(config_dict, lod_available=lod_available)
    out_path = out_dir / "manifest.json"
    write_json(out_path, manifest)
    print(f"Manifest written → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
