# pipeline/scripts/manifest.py
"""Build a MapManifest dict from a map config."""


def build_manifest(config: dict, lod_available: bool = True) -> dict:
    """Assemble the manifest.json structure from a map config dict."""
    r = float(config.get("radius_m", 500.0))
    assets: dict = {
        "terrain": "terrain.glb",
        "roads": "roads.glb",
        "buildings": "buildings.glb",
        "vegetation": "vegetation.glb",
        "vegetationData": "vegetation.json",
    }
    if lod_available:
        assets["terrainLod1"] = "terrain_lod1.glb"
        assets["terrainLod2"] = "terrain_lod2.glb"
    return {
        "name": config["name"],
        "displayName": config["displayName"],
        "spawnPosition": config["spawn_position"],
        "spawnRotation": config["spawn_rotation"],
        "startLine": config["start_line"],
        "finishLine": config["finish_line"],
        "checkpoints": config.get("checkpoints", []),
        "assets": assets,
        "roadGraph": "road-graph.json",
        "bounds": {
            "min": {"x": -r, "y": -50.0, "z": -r},
            "max": {"x": r, "y": 500.0, "z": r},
        },
    }
