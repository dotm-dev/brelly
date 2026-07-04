import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from formats.terrain import encode_heightmap


def test_output_shape_and_dtype():
    heights = [[0.0, 1.0], [2.0, 3.0]]
    u16, position_z, max_height = encode_heightmap(heights)
    assert u16.shape == (2, 2)
    assert u16.dtype == np.uint16


def test_margin_keeps_extremes_off_the_rails():
    # With margin_frac=0.1: span=15, margin=2.5, position_z=-7.5, max_height=20.
    # Lowest cell (-5) sits at 2.5/20 of the range -> 8192; highest (10) at 17.5/20 -> 57344.
    heights = [[-5.0, 0.0], [5.0, 10.0]]
    u16, position_z, max_height = encode_heightmap(heights)
    lowest, highest = int(u16[0, 0]), int(u16[1, 1])
    assert 0 < lowest < 16384        # off the floor, in the lower quarter
    assert 49152 < highest < 65535   # off the ceiling, in the upper quarter


def test_roundtrip_with_documented_decode_formula():
    # BeamNG docs: heightMeters = storedHeight * (maxHeight / 65536)
    heights = [[-5.0, 0.0], [5.0, 10.0]]
    u16, position_z, max_height = encode_heightmap(heights)
    decoded = position_z + u16.astype(float) * (max_height / 65536.0)
    original = np.array(heights)
    assert np.allclose(decoded, original, atol=0.01)


def test_flat_terrain_does_not_divide_by_zero():
    heights = [[3.0, 3.0], [3.0, 3.0]]
    u16, position_z, max_height = encode_heightmap(heights)
    assert max_height > 0
    assert not np.isnan(u16).any()
