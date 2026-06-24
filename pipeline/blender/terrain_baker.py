# pipeline/blender/terrain_baker.py
"""Blender script: load heightmap at full resolution and export as GLB.

Called by: blender --background --python terrain_baker.py -- <data_json> <out_glb> [texture_path]
data_json: {"width": N, "height": M, "heights": [[...], ...], "cell_size": float}

Full-resolution mode: no subsampling, no normal map bake. Every heightmap cell
becomes a mesh vertex. Use this to evaluate data quality before optimising for
rendering performance.
"""
import sys
import json
import os

argv = sys.argv
if "--" in argv:
    script_args = argv[argv.index("--") + 1:]
else:
    print("ERROR: Expected arguments after '--'")
    sys.exit(1)

data_json_path = script_args[0]
out_glb_path   = script_args[1]
texture_path   = script_args[2] if len(script_args) > 2 else None

import bpy
import bmesh

with open(data_json_path) as f:
    data = json.load(f)

heights = data["heights"]
cell    = data["cell_size"]
rows    = len(heights)
cols    = len(heights[0]) if rows else 0

bpy.ops.wm.read_factory_settings(use_empty=True)

print(f"Building terrain mesh ({rows}x{cols})...", flush=True)

mesh = bpy.data.meshes.new("terrain")
bm   = bmesh.new()
uv_layer = bm.loops.layers.uv.new("UVMap")

verts = []
for r in range(rows):
    row_verts = []
    for c in range(cols):
        x = c * cell - (cols * cell / 2)
        z = r * cell - (rows * cell / 2)
        y = heights[r][c]
        row_verts.append(bm.verts.new((x, z, y)))
    verts.append(row_verts)

bm.verts.ensure_lookup_table()

for r in range(rows - 1):
    for c in range(cols - 1):
        face = bm.faces.new([verts[r][c], verts[r][c+1], verts[r+1][c+1], verts[r+1][c]])
        face.loops[0][uv_layer].uv = (c / (cols - 1),       r / (rows - 1))
        face.loops[1][uv_layer].uv = ((c+1) / (cols - 1),   r / (rows - 1))
        face.loops[2][uv_layer].uv = ((c+1) / (cols - 1),   (r+1) / (rows - 1))
        face.loops[3][uv_layer].uv = (c / (cols - 1),       (r+1) / (rows - 1))

bm.to_mesh(mesh)
bm.free()

for poly in mesh.polygons:
    poly.use_smooth = True

obj = bpy.data.objects.new("terrain", mesh)
bpy.context.scene.collection.objects.link(obj)

# ── Material ──────────────────────────────────────────────────────────────────
if texture_path:
    mat = bpy.data.materials.new(name="terrain")
    mat.use_nodes = True
    tree  = mat.node_tree
    nodes = tree.nodes
    links = tree.links

    bsdf     = nodes.get("Principled BSDF")
    uv_node  = nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = "UVMap"
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(os.path.abspath(texture_path))
    tex_node.image.colorspace_settings.name = "sRGB"

    links.new(uv_node.outputs["UV"],    tex_node.inputs["Vector"])
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0

    mesh.materials.append(mat)
    print(f"Texture applied: {texture_path}", flush=True)
else:
    print("No texture — exporting untextured terrain", flush=True)

# ── Export ────────────────────────────────────────────────────────────────────
bpy.ops.export_scene.gltf(
    filepath=out_glb_path,
    export_format="GLB",
    use_selection=False,
    export_image_format="JPEG",
)
print(f"Terrain exported -> {out_glb_path}", flush=True)
