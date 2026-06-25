import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json, struct, importlib.util

# 02_terrain.py starts with a digit so use importlib
spec = importlib.util.spec_from_file_location(
    "terrain", Path(__file__).parent.parent / "scripts" / "02_terrain.py"
)
terrain_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terrain_mod)
write_terrain_glb = terrain_mod.write_terrain_glb


def _tile_count(glb_path: Path) -> int:
    data = glb_path.read_bytes()
    json_len = struct.unpack_from('<I', data, 12)[0]
    gltf = json.loads(data[20:20 + json_len])
    return len(gltf.get('nodes', []))


def test_force_tiles_overrides_natural_tiling(tmp_path):
    heights = [[float(r + c) for c in range(60)] for r in range(60)]
    out = tmp_path / "terrain.glb"
    write_terrain_glb(heights, cell=1.0, texture_path=None,
                      out_path=out, force_tiles=(2, 2))
    assert _tile_count(out) == 4


def test_no_force_tiles_behaves_as_before(tmp_path):
    heights = [[float(r + c) for c in range(60)] for r in range(60)]
    out = tmp_path / "terrain.glb"
    write_terrain_glb(heights, cell=1.0, texture_path=None,
                      out_path=out, force_tiles=None)
    assert _tile_count(out) == 1
