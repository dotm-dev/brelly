#!/usr/bin/env python3
# pipeline/scripts/08_lod.py
"""Generate terrain_lod1.glb (4× sub) and terrain_lod2.glb (16× sub)."""
import sys, math, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.io import read_json, output_dir

# Load TARGET_TILE_VERTS from 02_terrain.py so tile counts stay in sync.
_terrain_spec = importlib.util.spec_from_file_location(
    "_terrain_const", Path(__file__).parent / "02_terrain.py"
)
_terrain_const_mod = importlib.util.module_from_spec(_terrain_spec)
_terrain_spec.loader.exec_module(_terrain_const_mod)
TARGET_TILE_VERTS = _terrain_const_mod.TARGET_TILE_VERTS


def subsample(heights: list[list[float]], factor: int) -> list[list[float]]:
    """Return every factor-th row and column of heights."""
    return [row[::factor] for row in heights[::factor]]


def lod_tile_counts(rows: int, cols: int) -> tuple[int, int]:
    """Return (n_tiles_x, n_tiles_y) that write_terrain_glb would use naturally."""
    n_tiles_x = max(1, math.ceil(cols / TARGET_TILE_VERTS))
    n_tiles_y = max(1, math.ceil(rows / TARGET_TILE_VERTS))
    return n_tiles_x, n_tiles_y


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    out_dir = output_dir(config_dict)

    # Re-load the height grid (same source as 02_terrain.py).
    terrain_spec = importlib.util.spec_from_file_location(
        "terrain", Path(__file__).parent / "02_terrain.py"
    )
    terrain_mod = importlib.util.module_from_spec(terrain_spec)
    terrain_spec.loader.exec_module(terrain_mod)
    write_terrain_glb = terrain_mod.write_terrain_glb
    data = terrain_mod._load_or_synthesize_heightmap(config_dict)

    heights = data["heights"]
    cell = data["cell_size"]
    rows = len(heights)
    cols = len(heights[0]) if rows else 0

    # Compute the same tile grid as the full-res terrain so tiles pair 1-to-1 by index.
    force_tiles = lod_tile_counts(rows=rows, cols=cols)

    for factor, name in [(4, "terrain_lod1.glb"), (16, "terrain_lod2.glb")]:
        lod_heights = subsample(heights, factor)
        lod_cell = cell * factor
        out_path = out_dir / name
        print(f"  LOD {factor}× → {name} …", flush=True)
        write_terrain_glb(lod_heights, lod_cell, None, out_path, force_tiles=force_tiles)
        print(f"  LOD {factor}× → {name} done")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
