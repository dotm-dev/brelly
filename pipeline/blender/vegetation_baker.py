# pipeline/blender/vegetation_baker.py
"""Blender script: place low-poly cone trees at vegetation positions and export as GLB.

Called by: blender --background --python vegetation_baker.py -- <vegetation_json> <out_glb>
vegetation_json: {"positions": [{"x":..., "y":..., "z":...}, ...]}
"""
import sys
import json
import math

argv = sys.argv
script_args = argv[argv.index("--") + 1:] if "--" in argv else []
if len(script_args) < 2:
    print("ERROR: Expected <vegetation_json> <out_glb>")
    sys.exit(1)

veg_json_path, out_glb_path = script_args[0], script_args[1]

import bpy
import bmesh
from mathutils import Vector
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(__file__))
from baker_utils import load_terrain, snap_z, remove_object

with open(veg_json_path) as f:
    data = json.load(f)

positions = data.get("positions", [])

bpy.ops.wm.read_factory_settings(use_empty=True)

terrain_obj = load_terrain(out_glb_path)

# Cone geometry: 8 sides, height 4 m, base radius 1.5 m
SIDES = 8
HEIGHT = 4.0
RADIUS = 1.5
TREE_LIFT = 0.0   # snap_z already lifts off terrain; we want roots at surface

all_bm = bmesh.new()

for pos in positions:
    cx, cy = pos["x"], pos["z"]   # ENU: x=East, z=North (same convention as roads)
    base_z = snap_z(terrain_obj, cx, cy, pos["y"], lift=TREE_LIFT)
    tip_z = base_z + HEIGHT

    tip = all_bm.verts.new((cx, cy, tip_z))
    ring = []
    for i in range(SIDES):
        angle = 2 * math.pi * i / SIDES
        vx = cx + RADIUS * math.cos(angle)
        vy = cy + RADIUS * math.sin(angle)
        ring.append(all_bm.verts.new((vx, vy, base_z)))

    # side triangles
    for i in range(SIDES):
        all_bm.faces.new([ring[i], ring[(i + 1) % SIDES], tip])
    # base cap
    all_bm.faces.new(ring)

mesh = bpy.data.meshes.new("vegetation")
all_bm.to_mesh(mesh)
all_bm.free()

mat = bpy.data.materials.new(name="vegetation")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.15, 0.40, 0.12, 1)

mesh.materials.append(mat)
obj = bpy.data.objects.new("vegetation", mesh)
bpy.context.scene.collection.objects.link(obj)

if terrain_obj:
    remove_object(terrain_obj)

bpy.ops.export_scene.gltf(filepath=out_glb_path, export_format="GLB", use_selection=False)
print(f"Vegetation exported → {out_glb_path} ({len(positions)} trees)")
