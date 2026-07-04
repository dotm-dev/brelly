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


def write_ter_file(path: Path, heightmap_u16: np.ndarray, materials: list[str]) -> None:
    """Write BeamNG's binary .ter format: version(u8), size(u32),
    heightMap(u16 le array, row-major), layerMap(u8 array, row-major material
    index), materialCount(u32), materialNames(null-terminated UTF-8 strings).

    v1 always writes a flat layerMap (every cell = material index 0) — no
    per-pixel texture painting yet.
    """
    size = heightmap_u16.shape[0]
    assert heightmap_u16.shape == (size, size), "heightmap must be square"

    layer_map = np.zeros((size, size), dtype=np.uint8)

    with open(path, "wb") as f:
        f.write(struct.pack("<B", 8))
        f.write(struct.pack("<I", size))
        f.write(heightmap_u16.astype("<u2").tobytes())
        f.write(layer_map.tobytes())
        f.write(struct.pack("<I", len(materials)))
        for name in materials:
            f.write(name.encode("utf-8") + b"\x00")


def write_terrain_json(path: Path, size: int, ter_rel_path: str,
                        heightmap_png_rel_path: str, materials: list[str]) -> None:
    data = {
        "version": 8,
        "datafile": ter_rel_path,
        "heightmapImage": heightmap_png_rel_path,
        "size": size,
        "binaryFormat": (
            "version(u8), size(u32), heightMap(u16 le array), "
            "layerMap(u8 array), materialCount(u32), "
            "materialNames(null-terminated utf8 strings)"
        ),
        "heightMapSize": size * size,
        "heightMapItemSize": 2,
        "layerMapSize": size * size,
        "layerMapItemSize": 1,
        "materials": materials,
    }
    path.write_text(json.dumps(data, indent=2))


def write_heightmap_png(path: Path, heightmap_u16: np.ndarray) -> None:
    """16-bit grayscale PNG — BeamNG docs: 'Heightmaps must be 16-bit PNG
    to preserve elevation details.'"""
    from PIL import Image
    img = Image.fromarray(heightmap_u16, mode="I;16")
    img.save(path)


def terrainblock_object(name: str, position_xyz: tuple[float, float, float],
                         square_size: float, max_height: float,
                         terrain_file_rel: str) -> dict:
    x, y, z = position_xyz
    return {
        "class": "TerrainBlock",
        "name": name,
        "position": [round(x, 3), round(y, 3), round(z, 3)],
        "terrainFile": terrain_file_rel,
        "squareSize": round(square_size, 4),
        "maxHeight": round(max_height, 3),
    }
