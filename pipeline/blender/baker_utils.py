# pipeline/blender/baker_utils.py
"""Shared constants and helpers for Blender baker scripts."""
from pathlib import Path

ROAD_LIFT = 1.2  # metres above surveyed TLM elevation — absorbs DEM/TLM disagreement on steep slopes
MAX_MITER = 3.0


def load_terrain(out_glb_path: str):
    """Import terrain.glb from the same directory, join all tile meshes, return combined obj."""
    import bpy
    terrain_path = str(Path(out_glb_path).parent / "terrain.glb")
    if not Path(terrain_path).exists():
        print(f"WARNING: terrain.glb not found at {terrain_path} — skipping terrain snap")
        return None
    try:
        before = set(bpy.data.objects.keys())
        bpy.ops.import_scene.gltf(filepath=terrain_path)
        new_objs = [o for o in bpy.context.scene.objects
                    if o.name not in before and o.type == "MESH"]
        if not new_objs:
            return None
        # Apply each object's transform (glTF Y-up → Blender Z-up rotation) so that
        # vertex data is in Blender world space before raycasting. Must be done even
        # for single-tile terrain — skipping this causes snap_z to raycast in glTF
        # local space (Y=elevation, Z=-north) and return wrong results.
        bpy.ops.object.select_all(action="DESELECT")
        for o in new_objs:
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            o.select_set(False)

        if len(new_objs) == 1:
            return new_objs[0]

        for o in new_objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = new_objs[0]
        bpy.ops.object.join()
        return bpy.context.view_layer.objects.active
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
