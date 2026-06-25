# pipeline/blender/building_baker.py
"""Blender script: extrude building footprints into 3D volumes and export as GLB.

Called by: blender --background --python building_baker.py -- <buildings_json> <out_glb>
buildings_json: [{"footprint": [[x,z],...], "height": 8.0, "base_y": 0.0}, ...]
"""
import sys
import json

argv = sys.argv
script_args = argv[argv.index("--") + 1:] if "--" in argv else []
if len(script_args) < 2:
    print("ERROR: Expected <buildings_json> <out_glb>")
    sys.exit(1)

buildings_json_path, out_glb_path = script_args[0], script_args[1]

import bpy
import bmesh

with open(buildings_json_path) as f:
    buildings = json.load(f)

bpy.ops.wm.read_factory_settings(use_empty=True)

def _centroid(pts):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return cx, cy


def _footprint_width(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(max(xs) - min(xs), max(ys) - min(ys))


for idx, building in enumerate(buildings):
    footprint = building["footprint"]
    height = building.get("height", 8.0)
    base_y = building.get("base_y", 0.0)
    roof = building.get("roof", "pitched")

    if len(footprint) < 3:
        continue

    bm = bmesh.new()
    bottom_verts = [bm.verts.new((pt[0], pt[1], base_y)) for pt in footprint]
    top_verts = [bm.verts.new((pt[0], pt[1], base_y + height)) for pt in footprint]

    bm.faces.new(bottom_verts)
    n = len(footprint)

    if roof == "pitched" and n >= 4:
        cx, cy = _centroid(footprint)
        ridge_z = base_y + height + 0.3 * _footprint_width(footprint)
        ridge = bm.verts.new((cx, cy, ridge_z))
        for i in range(n):
            bm.faces.new([top_verts[i], top_verts[(i + 1) % n], ridge])
    else:
        bm.faces.new(top_verts[::-1])

    for i in range(n):
        bm.faces.new([bottom_verts[i], bottom_verts[(i+1) % n],
                      top_verts[(i+1) % n], top_verts[i]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(f"building_{idx}")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"building_{idx}", mesh)
    bpy.context.scene.collection.objects.link(obj)

bpy.ops.export_scene.gltf(filepath=out_glb_path, export_format="GLB", use_selection=False)
print(f"Buildings exported → {out_glb_path}")
