# pipeline/blender/road_baker.py
"""Blender script: extrude road centerlines into drivable road meshes and export as GLB.

Called by: blender --background --python road_baker.py -- <roads_json> <out_glb>
roads_json: [{"coords": [[x,y,z],...], "width": 6.0, "road_type": "road_main"}, ...]

Elevation: uses the surveyed Z from Swiss TLM directly — no terrain raycasting.
"""
import sys
import json

argv = sys.argv
script_args = argv[argv.index("--") + 1:] if "--" in argv else []
if len(script_args) < 2:
    print("ERROR: Expected <roads_json> <out_glb>")
    sys.exit(1)

roads_json_path, out_glb_path = script_args[0], script_args[1]

import bpy
import bmesh
from mathutils import Vector
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.dirname(__file__))
from baker_utils import ROAD_LIFT, MAX_MITER

with open(roads_json_path) as f:
    roads = json.load(f)

bpy.ops.wm.read_factory_settings(use_empty=True)


def _to_blender(pt) -> Vector:
    """ENU [East, elevation, North] → Blender (East, North, elevation + lift)."""
    return Vector((pt[0], pt[2], pt[1] + ROAD_LIFT))


def _horiz(v):
    return Vector((v.x, v.y, 0))


def _miter_perp(pts, i, half_w):
    """Miter-corrected lateral offset at point i, scaled by 1/cos(half_angle)."""
    n = len(pts)

    def safe_dir(a, b):
        d = _horiz(b - a)
        return d.normalized() if d.length > 1e-4 else None

    if i == 0:
        d = safe_dir(pts[0], pts[1]) or Vector((1, 0, 0))
        d_in, d_out = d, d
    elif i == n - 1:
        d = safe_dir(pts[n - 2], pts[n - 1]) or Vector((1, 0, 0))
        d_in, d_out = d, d
    else:
        d_in  = safe_dir(pts[i - 1], pts[i])
        d_out = safe_dir(pts[i],     pts[i + 1])
        if d_in is None and d_out is None:
            d_in = d_out = Vector((1, 0, 0))
        elif d_in is None:
            d_in = d_out
        elif d_out is None:
            d_out = d_in

    bisector = (d_in + d_out)
    if bisector.length < 1e-6:
        bisector = d_out
    bisector = bisector.normalized()

    miter = Vector((-bisector.y, bisector.x, 0))

    out_perp = Vector((-d_out.y, d_out.x, 0))
    cos_a = abs(miter.dot(out_perp))
    scale = 1.0 / max(cos_a, 1.0 / MAX_MITER)

    return miter * half_w * scale


# ── Build one mesh per road type ─────────────────────────────────────────────
from collections import defaultdict

bm_by_type = defaultdict(bmesh.new)

for road in roads:
    coords = road["coords"]
    half_w = road["width"] / 2.0
    road_type = road.get("road_type", "road_local")
    if len(coords) < 2:
        continue

    pts = [_to_blender(c) for c in coords]
    perps = [_miter_perp(pts, i, half_w) for i in range(len(pts))]

    left  = [pts[i] + perps[i] for i in range(len(pts))]
    right = [pts[i] - perps[i] for i in range(len(pts))]

    bm = bm_by_type[road_type]
    verts_l = [bm.verts.new(v) for v in left]
    verts_r = [bm.verts.new(v) for v in right]

    for i in range(len(pts) - 1):
        bm.faces.new([verts_l[i], verts_r[i], verts_r[i + 1], verts_l[i + 1]])

_TYPE_COLOR = {
    "road_major": (0.20, 0.20, 0.24, 1),
    "road_main":  (0.25, 0.25, 0.28, 1),
    "road_local": (0.30, 0.30, 0.33, 1),
    "road_small": (0.35, 0.35, 0.37, 1),
    "path":       (0.45, 0.40, 0.35, 1),
}

for road_type, bm in bm_by_type.items():
    mesh = bpy.data.meshes.new(road_type)
    bm.to_mesh(mesh)
    bm.free()
    mat = bpy.data.materials.new(name=road_type)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = _TYPE_COLOR.get(road_type, (0.3, 0.3, 0.3, 1))
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(road_type, mesh)
    bpy.context.scene.collection.objects.link(obj)

bpy.ops.export_scene.gltf(filepath=out_glb_path, export_format="GLB", use_selection=False)
print(f"Roads exported → {out_glb_path}")
