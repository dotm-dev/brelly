import sys, json, struct, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

spec = importlib.util.spec_from_file_location(
    "lod", Path(__file__).parent.parent / "scripts" / "08_lod.py"
)
lod_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lod_mod)
subsample = lod_mod.subsample
lod_tile_counts = lod_mod.lod_tile_counts


def test_subsample_factor_4():
    heights = [[float(r * 100 + c) for c in range(100)] for r in range(100)]
    result = subsample(heights, factor=4)
    assert len(result) == 25       # 100 / 4 = 25 rows
    assert len(result[0]) == 25    # 25 cols
    assert result[0][0] == heights[0][0]
    assert result[1][0] == heights[4][0]


def test_subsample_factor_16():
    heights = [[float(r * 100 + c) for c in range(100)] for r in range(100)]
    result = subsample(heights, factor=16)
    assert len(result) == 7        # ceil(100 / 16) = 7 (indices 0,16,32,48,64,80,96)
    assert len(result[0]) == 7


def test_subsample_preserves_corner_values():
    heights = [[float(r + c) for c in range(64)] for r in range(64)]
    result = subsample(heights, factor=4)
    assert result[0][0] == heights[0][0]
    assert result[-1][-1] == heights[60][60]


def test_lod_tile_counts_matches_natural_tiling():
    """lod_tile_counts returns the natural tile count for a given grid size."""
    nx, ny = lod_tile_counts(rows=4000, cols=4000)
    assert nx == 8
    assert ny == 8


def test_lod_tile_counts_small_grid():
    nx, ny = lod_tile_counts(rows=200, cols=200)
    assert nx == 1
    assert ny == 1
