import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))

spec = importlib.util.spec_from_file_location(
    "beamng_package_step", Path(__file__).parent.parent / "scripts" / "02_package.py"
)
package_step = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_step)


def _write_config(tmp_path: Path) -> Path:
    config = {
        "name": "test_area",
        "displayName": "Test Area",
        "spawn_position": {"x": 3.0, "y": 1.0, "z": -45.0},
    }
    config_path = tmp_path / "test_area.json"
    config_path.write_text(json.dumps(config))
    return config_path


def test_main_merges_objects_and_writes_shell(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_config(tmp_path)

    out_dir = tmp_path / "maps" / "test_area" / "beamng" / "test_area"
    out_dir.mkdir(parents=True)
    (out_dir / "_terrain_objects.json").write_text(json.dumps([{"class": "TerrainBlock", "name": "t"}]))
    (out_dir / "_road_objects.json").write_text(json.dumps([{"class": "DecalRoad", "name": "r"}]))

    package_step.main(str(config_path))

    items_path = out_dir / "main" / "items.level.json"
    lines = items_path.read_text().strip().split("\n")
    assert json.loads(lines[0])["class"] == "TerrainBlock"
    assert json.loads(lines[1])["class"] == "DecalRoad"

    # config spawn_position is glTF-frame (x=east, y=up, z=-north); BeamNG gets
    # (east, north, up + 1m clearance)
    spawn = json.loads(lines[2])
    assert spawn["class"] == "SpawnSphere"
    assert spawn["name"] == "spawn_default"
    assert spawn["position"] == [3.0, 45.0, 2.0]

    assert not (out_dir / "_terrain_objects.json").exists()
    assert not (out_dir / "_road_objects.json").exists()

    info = json.loads((out_dir / "info.json").read_text())
    assert info["description"] == "Test Area"
    assert info["spawnPoints"][0]["objectname"] == "spawn_default"

    level = json.loads((out_dir / "level.json").read_text())
    assert level["name"] == "Test Area"


def test_main_handles_missing_road_objects_and_spawn(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = {"name": "test_area", "displayName": "Test Area"}   # no spawn_position
    config_path = tmp_path / "test_area.json"
    config_path.write_text(json.dumps(config))
    out_dir = tmp_path / "maps" / "test_area" / "beamng" / "test_area"
    out_dir.mkdir(parents=True)
    (out_dir / "_terrain_objects.json").write_text(json.dumps([{"class": "TerrainBlock", "name": "t"}]))

    package_step.main(str(config_path))

    items_path = out_dir / "main" / "items.level.json"
    lines = items_path.read_text().strip().split("\n")
    # terrain + fallback spawn at map origin
    assert len(lines) == 2
    assert json.loads(lines[1])["class"] == "SpawnSphere"
