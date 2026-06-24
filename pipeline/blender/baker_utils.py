# pipeline/blender/baker_utils.py
"""Shared constants and helpers for Blender baker scripts."""
from pathlib import Path

ROAD_LIFT = 1.2  # metres above surveyed TLM elevation — absorbs DEM/TLM disagreement on steep slopes
MAX_MITER = 3.0


def load_terrain(out_glb_path: str):
    """Import terrain.glb from the same directory as out_glb_path. Returns mesh obj or None."""
    import bpy
    terrain_path = str(Path(out_glb_path).parent / "terrain.glb")
    if not Path(terrain_path).exists():
        print(f"WARNING: terrain.glb not found at {terrain_path} — skipping terrain snap")
        return None
    try:
        bpy.ops.import_scene.gltf(filepath=terrain_path)
        # prefer an object whose name contains "terrain"
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH" and "terrain" in obj.name.lower():
                return obj
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH":
                return obj
    except Exception as e:
        print(f"WARNING: Could not load terrain.glb: {e}")
    return None


def snap_z(terrain_obj, x: float, y: float, fallback_z: float, lift: float = 0.0) -> float:
    """Raycast downward onto terrain_obj from (x, y). Returns terrain Z + lift, or fallback + lift."""
    if terrain_obj is None:
        return fallback_z + lift
    hit, location, _, _ = terrain_obj.ray_cast((x, y, 9999.0), (0.0, 0.0, -1.0))
    return (location[2] if hit else fallback_z) + lift


def remove_object(obj) -> None:
    """Remove a Blender object and its mesh data from the scene."""
    import bpy
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh and mesh.users == 0:
        bpy.data.meshes.remove(mesh)
