import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest

PIL_Image = pytest.importorskip("PIL.Image")

from formats.terrain import write_heightmap_png, terrainblock_object


def test_heightmap_png_is_16bit_and_roundtrips(tmp_path):
    u16 = np.array([[0, 100], [200, 65535]], dtype=np.uint16)
    out_path = tmp_path / "test_heightmap.png"
    write_heightmap_png(out_path, u16)

    img = PIL_Image.open(out_path)
    # Pillow reports 16-bit grayscale PNGs as "I;16" or "I" depending on version;
    # what matters is that the pixel values survive the roundtrip losslessly.
    assert img.mode in ("I;16", "I")
    loaded = np.array(img).astype(np.uint16)
    assert np.array_equal(loaded, u16)


def test_terrainblock_object_fields():
    obj = terrainblock_object(
        name="bre_terrain",
        position_xyz=(-500.0, -500.0, -12.345),
        square_size=0.9766,
        max_height=123.456,
        terrain_file_rel="art/terrains/bre.ter",
    )
    assert obj["class"] == "TerrainBlock"
    assert obj["name"] == "bre_terrain"
    assert obj["position"] == [-500.0, -500.0, -12.345]
    assert obj["terrainFile"] == "art/terrains/bre.ter"
    assert obj["squareSize"] == 0.9766
    assert obj["maxHeight"] == 123.456
