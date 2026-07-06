#!/usr/bin/env python3
# pipeline_beamng/scripts/02_package.py
"""Assemble the BeamNG level folder: merge terrain + road scene objects (plus
a default spawn point — the docs require every level to include one) into the
main/MissionGroup SimGroup hierarchy real BeamNG levels use, and write
info.json (level metadata lives there, not in a separate level.json)."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))

from utils.io import read_json
from formats.coords import road_node_to_beamng
from formats.road import write_items_level_json


def _resolve_radius_m(config_dict: dict) -> float:
    """Same radius_m the terrain/road steps use: explicit config value, else
    auto-detected from the DEM (00_terrain.py already logged this once)."""
    if "radius_m" in config_dict:
        return float(config_dict["radius_m"])
    dem_path = config_dict.get("source_data", {}).get("dem")
    if not dem_path or "center_e" not in config_dict or "center_n" not in config_dict:
        return 0.0
    from utils.coords import radius_from_dem
    detected = radius_from_dem(dem_path, float(config_dict["center_e"]), float(config_dict["center_n"]))
    return detected or 500.0


def _sim_group(name: str) -> dict:
    return {"name": name, "class": "SimGroup", "persistentId": str(uuid.uuid4())}


def _spawn_object(config_dict: dict) -> dict:
    """Default SpawnSphere from the config's spawn_position (glTF frame:
    x=east, y=up, z=-north), lifted 1m to avoid spawning inside the ground.
    Falls back to the map origin when the config has no spawn_position."""
    spawn = config_dict.get("spawn_position", {"x": 0.0, "y": 1.0, "z": 0.0})
    bx, by, bz = road_node_to_beamng(float(spawn["x"]), float(spawn["y"]), float(spawn["z"]))
    return {
        "class": "SpawnSphere",
        "name": "spawn_default",
        "position": [round(bx, 3), round(by, 3), round(bz + 1.0, 3)],
    }


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    name = config_dict["name"]
    display_name = config_dict.get("displayName", name)

    out_dir = Path("maps") / name / "beamng" / name
    main_dir = out_dir / "main"
    mission_dir = main_dir / "MissionGroup"
    level_object_dir = mission_dir / "level_object"
    terrain_dir = level_object_dir / "terrain"
    for d in (main_dir, mission_dir, level_object_dir, terrain_dir):
        d.mkdir(parents=True, exist_ok=True)

    terrain_objs_path = out_dir / "_terrain_objects.json"
    road_objs_path = out_dir / "_road_objects.json"
    terrain_objs = json.loads(terrain_objs_path.read_text()) if terrain_objs_path.exists() else []
    road_objs = json.loads(road_objs_path.read_text()) if road_objs_path.exists() else []

    # Real BeamNG levels nest scene objects in a SimGroup hierarchy across
    # folders rather than one flat items.level.json — mirror that so the
    # level opens correctly in BeamNG's World Editor.
    write_items_level_json(main_dir / "items.level.json", [_sim_group("MissionGroup")])
    write_items_level_json(
        mission_dir / "items.level.json",
        road_objs + [_spawn_object(config_dict), _sim_group("level_object")],
    )
    write_items_level_json(level_object_dir / "items.level.json", [_sim_group("terrain")])
    write_items_level_json(terrain_dir / "items.level.json", terrain_objs)

    terrain_objs_path.unlink(missing_ok=True)
    road_objs_path.unlink(missing_ok=True)

    radius_m = _resolve_radius_m(config_dict)
    info = {
        "title": display_name,
        "description": display_name,
        "author": "Brelly pipeline",
        "version": 1,
        "size": [radius_m * 2, radius_m * 2],
        "tags": ["brelly-export"],
        "defaultSpawnPointName": "spawn_default",
        "spawnPoints": [{"translationId": "Default Spawnpoint", "objectname": "spawn_default"}],
    }
    (out_dir / "info.json").write_text(json.dumps(info, indent=2))

    print(f"BeamNG level packaged -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
