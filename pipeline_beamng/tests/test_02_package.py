import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

    main_dir = out_dir / "main"
    top = [json.loads(l) for l in (main_dir / "items.level.json").read_text().strip().split("\n")]
    assert top[0]["class"] == "SimGroup"
    assert top[0]["name"] == "MissionGroup"

    mission_dir = main_dir / "MissionGroup"
    mission = [json.loads(l) for l in (mission_dir / "items.level.json").read_text().strip().split("\n")]
    assert mission[0]["class"] == "DecalRoad"

    # config spawn_position is glTF-frame (x=east, y=up, z=-north); BeamNG gets
    # (east, north, up + 1m clearance)
    spawn = mission[1]
    assert spawn["class"] == "SpawnSphere"
    assert spawn["name"] == "spawn_default"
    assert spawn["position"] == [3.0, 45.0, 2.0]
    assert mission[2]["class"] == "SimGroup"
    assert mission[2]["name"] == "level_object"

    level_object_dir = mission_dir / "level_object"
    level_object = [json.loads(l) for l in (level_object_dir / "items.level.json").read_text().strip().split("\n")]
    assert level_object[0]["class"] == "SimGroup"
    assert level_object[0]["name"] == "terrain"

    terrain_dir = level_object_dir / "terrain"
    terrain = [json.loads(l) for l in (terrain_dir / "items.level.json").read_text().strip().split("\n")]
    assert terrain[0]["class"] == "TerrainBlock"

    assert not (out_dir / "_terrain_objects.json").exists()
    assert not (out_dir / "_road_objects.json").exists()

    info = json.loads((out_dir / "info.json").read_text())
    assert info["title"] == "Test Area"
    assert info["description"] == "Test Area"
    assert info["defaultSpawnPointName"] == "spawn_default"
    assert info["spawnPoints"][0]["objectname"] == "spawn_default"

    assert not (out_dir / "level.json").exists()


def test_main_handles_missing_road_objects_and_spawn(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = {"name": "test_area", "displayName": "Test Area"}   # no spawn_position
    config_path = tmp_path / "test_area.json"
    config_path.write_text(json.dumps(config))
    out_dir = tmp_path / "maps" / "test_area" / "beamng" / "test_area"
    out_dir.mkdir(parents=True)
    (out_dir / "_terrain_objects.json").write_text(json.dumps([{"class": "TerrainBlock", "name": "t"}]))

    package_step.main(str(config_path))

    terrain_dir = out_dir / "main" / "MissionGroup" / "level_object" / "terrain"
    terrain = [json.loads(l) for l in (terrain_dir / "items.level.json").read_text().strip().split("\n")]
    assert len(terrain) == 1
    assert terrain[0]["class"] == "TerrainBlock"

    # no roads: MissionGroup has just the fallback spawn + level_object group
    mission_dir = out_dir / "main" / "MissionGroup"
    mission = [json.loads(l) for l in (mission_dir / "items.level.json").read_text().strip().split("\n")]
    assert len(mission) == 2
    assert mission[0]["class"] == "SpawnSphere"
    assert mission[1]["class"] == "SimGroup"
