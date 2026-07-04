import json
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from formats.terrain import write_ter_file, write_terrain_json


def test_ter_file_header_and_size(tmp_path):
    u16 = np.array([[0, 100], [200, 65535]], dtype=np.uint16)
    out_path = tmp_path / "test.ter"
    write_ter_file(out_path, u16, materials=["grass"])

    data = out_path.read_bytes()
    version = struct.unpack_from("<B", data, 0)[0]
    size = struct.unpack_from("<I", data, 1)[0]
    assert version == 8
    assert size == 2


def test_ter_file_heightmap_roundtrips(tmp_path):
    u16 = np.array([[0, 100], [200, 65535]], dtype=np.uint16)
    out_path = tmp_path / "test.ter"
    write_ter_file(out_path, u16, materials=["grass"])

    data = out_path.read_bytes()
    offset = 1 + 4   # version + size
    heightmap_bytes = 2 * 2 * 2   # size*size cells * 2 bytes
    heightmap = np.frombuffer(data[offset:offset + heightmap_bytes], dtype="<u2").reshape(2, 2)
    assert np.array_equal(heightmap, u16)


def test_ter_file_material_names_roundtrip(tmp_path):
    u16 = np.zeros((2, 2), dtype=np.uint16)
    out_path = tmp_path / "test.ter"
    write_ter_file(out_path, u16, materials=["grass", "asphalt"])

    data = out_path.read_bytes()
    offset = 1 + 4 + (2 * 2 * 2) + (2 * 2 * 1)   # version+size+heightmap+layermap
    material_count = struct.unpack_from("<I", data, offset)[0]
    assert material_count == 2
    rest = data[offset + 4:].split(b"\x00")
    assert rest[0] == b"grass"
    assert rest[1] == b"asphalt"


def test_terrain_json_fields(tmp_path):
    out_path = tmp_path / "test.terrain.json"
    write_terrain_json(
        out_path, size=2,
        ter_rel_path="art/terrains/test.ter",
        heightmap_png_rel_path="art/terrains/test_heightmap.png",
        materials=["grass"],
    )
    data = json.loads(out_path.read_text())
    assert data["size"] == 2
    assert data["datafile"] == "art/terrains/test.ter"
    assert data["heightmapImage"] == "art/terrains/test_heightmap.png"
    assert data["heightMapSize"] == 4
    assert data["heightMapItemSize"] == 2
    assert data["layerMapSize"] == 4
    assert data["layerMapItemSize"] == 1
    assert data["materials"] == ["grass"]
