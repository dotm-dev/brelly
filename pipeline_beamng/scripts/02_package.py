#!/usr/bin/env python3
# pipeline_beamng/scripts/02_package.py
"""Assemble the BeamNG level folder: merge terrain + road scene objects (plus
a default spawn point — the docs require every level to include one) into
main/items.level.json, and write info.json / level.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))

from utils.io import read_json
from formats.coords import road_node_to_beamng
from formats.road import write_items_level_json


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
    main_dir.mkdir(parents=True, exist_ok=True)

    terrain_objs_path = out_dir / "_terrain_objects.json"
    road_objs_path = out_dir / "_road_objects.json"
    terrain_objs = json.loads(terrain_objs_path.read_text()) if terrain_objs_path.exists() else []
    road_objs = json.loads(road_objs_path.read_text()) if road_objs_path.exists() else []

    objects = terrain_objs + road_objs + [_spawn_object(config_dict)]
    write_items_level_json(main_dir / "items.level.json", objects)

    terrain_objs_path.unlink(missing_ok=True)
    road_objs_path.unlink(missing_ok=True)

    info = {
        "author": "Brelly pipeline",
        "version": 1,
        "description": display_name,
        "tags": ["brelly-export"],
        "spawnPoints": [{"objectname": "spawn_default"}],
    }
    (out_dir / "info.json").write_text(json.dumps(info, indent=2))

    level = {"name": display_name}
    (out_dir / "level.json").write_text(json.dumps(level, indent=2))

    print(f"BeamNG level packaged -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
