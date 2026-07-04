"""BeamNG DecalRoad scene object builder and the line-delimited
items.level.json writer. Field set is best-effort from documentation
(see [[reference_beamng_file_formats]] in project memory) — unverified
in-game."""
import json
from pathlib import Path


def decalroad_object(name: str, nodes: list[list[float]], material: str = "road_asphalt") -> dict:
    """nodes: list of [x, y, z, width] in BeamNG world coordinates."""
    return {
        "class": "DecalRoad",
        "name": name,
        "material": material,
        "textureLength": 8,
        "renderPriority": 10,
        "zBias": 0,
        "decalBias": 0,
        "distanceFade": [300, 50],
        "startEndFade": [5, 5],
        "overObjects": False,
        "hiddenInNavi": False,
        "drivability": 1,
        "autoLanes": True,
        "oneWay": False,
        "flipDirection": False,
        "gatedRoad": False,
        "autoJunction": True,
        "useSubdivisions": False,
        "improvedSpline": True,
        "smoothness": 0.5,
        "detail": 0.1,
        "looped": False,
        "startTangent": True,
        "endTangent": True,
        "breakAngle": 3,
        "nodes": nodes,
    }


def write_items_level_json(path: Path, objects: list[dict]) -> None:
    """items.level.json: one JSON object per line, not a single JSON array."""
    with open(path, "w", encoding="utf-8") as f:
        for obj in objects:
            f.write(json.dumps(obj, separators=(",", ":")))
            f.write("\n")
