"""BeamNG terrain file writers: .ter binary, .terrain.json, heightmap PNG,
and the TerrainBlock scene object. See [[reference_beamng_file_formats]] in
project memory for the documented format this implements."""
import json
import struct
from pathlib import Path

import numpy as np


def encode_heightmap(heights: list[list[float]], margin_frac: float = 0.1) -> tuple[np.ndarray, float, float]:
    """Normalize a relative-elevation grid into BeamNG's u16 heightmap encoding.

    Returns (heightmap_u16, position_z, max_height) where:
      position_z  = world Z (relative to base_elevation) the TerrainBlock is placed at
      max_height  = total elevation span the u16 range covers
      heightMeters(row, col) = position_z + heightmap_u16[row, col] * (max_height / 65536)
    """
    arr = np.array(heights, dtype=np.float64)
    lo, hi = float(arr.min()), float(arr.max())
    span = hi - lo
    margin = span * margin_frac + 1.0
    position_z = lo - margin
    max_height = span + 2 * margin
    # BeamNG's documented decode is storedHeight * (maxHeight / 65536), so encode
    # with 65536; the margin guarantees values never reach the u16 ceiling.
    normalized = (arr - position_z) / max_height
    u16 = np.clip(np.round(normalized * 65536.0), 0, 65535).astype(np.uint16)
    return u16, position_z, max_height
