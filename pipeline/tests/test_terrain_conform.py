import numpy as np
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._terrain_conform import conform_to_roads, RoadSegment

def _flat(n=20):
    return np.zeros((n, n), dtype=float)

def _make_seg(e0, n0, z0, e1, n1, z1, width=4.0):
    return RoadSegment(
        points=[(e0, n0, z0), (e1, n1, z1)],
        half_width=width / 2,
    )

def test_center_cell_raised():
    """Cell directly under road centre gets road elevation."""
    arr = _flat()
    seg = _make_seg(0, 10, 5.0, 19, 10, 5.0, width=4.0)
    conform_to_roads(arr, [seg], min_e=0.0, min_n=0.0, cell_size=1.0, blend_cells=2)
    assert arr[10, 10] == 5.0

def test_outside_blend_unchanged():
    """Cell far from road is untouched."""
    arr = _flat()
    seg = _make_seg(0, 10, 5.0, 19, 10, 5.0, width=4.0)
    conform_to_roads(arr, [seg], min_e=0.0, min_n=0.0, cell_size=1.0, blend_cells=2)
    assert arr[0, 0] == 0.0

def test_blend_zone_partial():
    """Cell in blend zone has value between 0 and road elevation."""
    arr = _flat()
    seg = _make_seg(0, 10, 10.0, 19, 10, 10.0, width=2.0)
    conform_to_roads(arr, [seg], min_e=0.0, min_n=0.0, cell_size=1.0, blend_cells=2)
    val = arr[13, 10]
    assert 0.0 < val < 10.0

def test_cut_lowers_terrain_when_road_below():
    """True cut-and-fill: road below terrain lowers the terrain to road level."""
    arr = np.full((20, 20), 20.0)
    seg = _make_seg(0, 10, 5.0, 19, 10, 5.0, width=4.0)   # cut_allowed=True by default
    conform_to_roads(arr, [seg], min_e=0.0, min_n=0.0, cell_size=1.0, blend_cells=2)
    assert arr[10, 10] == pytest.approx(5.0)


def test_fill_only_ignores_road_below_terrain():
    """With cut_allowed=False (legacy fill-only), road below terrain is ignored."""
    arr = np.full((20, 20), 20.0)
    seg = RoadSegment(points=[(0, 10, 5.0), (19, 10, 5.0)], half_width=2.0, cut_allowed=False)
    conform_to_roads(arr, [seg], min_e=0.0, min_n=0.0, cell_size=1.0, blend_cells=2)
    assert arr[10, 10] == 20.0
