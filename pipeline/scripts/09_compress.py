#!/usr/bin/env python3
# pipeline/scripts/09_compress.py
"""Run gltfpack on all GLB files in the output directory."""
import sys, subprocess, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))                # repo root, for shared/
from shared.utils.io import read_json, output_dir


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    out_dir = output_dir(config_dict)
    gltfpack = shutil.which("gltfpack")

    if not gltfpack:
        print("WARNING: gltfpack not found. Skipping compression.")
        return

    # terrain.glb is tiled (36 separate mesh nodes); gltfpack merges them into
    # one mesh which defeats the tiling and breaks WebGL index limits.
    glbs = sorted(p for p in out_dir.glob("*.glb") if p.name != "terrain.glb")
    total = len(glbs)
    for j, glb_path in enumerate(glbs, 1):
        label = f"[{j}/{total}] {glb_path.name}"
        print(f"  {label}...", flush=True)

        # General quantisation + compression for all GLBs
        result = subprocess.run(
            [gltfpack, "-i", str(glb_path), "-o", str(glb_path), "-cc"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  {label} compressed")
        else:
            print(f"WARNING: gltfpack failed on {glb_path.name}: {result.stderr[:200]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
