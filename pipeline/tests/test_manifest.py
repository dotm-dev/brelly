# pipeline/tests/test_manifest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.manifest import build_manifest


BASE_CONFIG = {
    "name": "test",
    "displayName": "Test Map",
    "center_e": 2683000.0,
    "center_n": 1247500.0,
    "base_elevation": 450.0,
    "radius_m": 500.0,
    "start_line": {
        "position": {"x": 0, "y": 0, "z": -50},
        "normal": {"x": 0, "y": 0, "z": 1},
        "widthMetres": 12,
    },
    "finish_line": {
        "position": {"x": 0, "y": 0, "z": 200},
        "normal": {"x": 0, "y": 0, "z": 1},
        "widthMetres": 12,
    },
    "spawn_position": {"x": 0, "y": 1, "z": -45},
    "spawn_rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
    "checkpoints": [],
    "source_data": {"dem": "data/alti3d.tif", "tlm": "data/tlm.gpkg"},
}


def test_manifest_has_required_keys():
    m = build_manifest(BASE_CONFIG)
    for key in ["name", "displayName", "spawnPosition", "spawnRotation",
                "startLine", "finishLine", "checkpoints", "assets", "roadGraph", "bounds"]:
        assert key in m, f"Missing key: {key}"


def test_manifest_name_matches_config():
    m = build_manifest(BASE_CONFIG)
    assert m["name"] == "test"
    assert m["displayName"] == "Test Map"


def test_manifest_start_finish_pass_through():
    m = build_manifest(BASE_CONFIG)
    assert m["startLine"]["position"]["z"] == -50
    assert m["finishLine"]["position"]["z"] == 200


def test_manifest_assets_point_to_correct_files():
    m = build_manifest(BASE_CONFIG)
    assert m["assets"]["terrain"] == "terrain.glb"
    assert m["assets"]["roads"] == "roads.glb"
    assert m["assets"]["buildings"] == "buildings.glb"
    assert m["assets"]["vegetationData"] == "vegetation.json"
    assert m["roadGraph"] == "road-graph.json"


def test_manifest_bounds_derived_from_radius():
    m = build_manifest(BASE_CONFIG)
    assert m["bounds"]["min"]["x"] == -500.0
    assert m["bounds"]["max"]["x"] == 500.0
    assert m["bounds"]["min"]["z"] == -500.0
    assert m["bounds"]["max"]["z"] == 500.0


def test_manifest_spawn_position_passes_through():
    m = build_manifest(BASE_CONFIG)
    assert m["spawnPosition"]["y"] == 1


def test_manifest_includes_terrain_lod_assets():
    m = build_manifest(BASE_CONFIG, lod_available=True)
    assert m["assets"]["terrainLod1"] == "terrain_lod1.glb"
    assert m["assets"]["terrainLod2"] == "terrain_lod2.glb"


def test_manifest_excludes_terrain_lod_when_not_available():
    m = build_manifest(BASE_CONFIG, lod_available=False)
    assert "terrainLod1" not in m["assets"]
    assert "terrainLod2" not in m["assets"]
