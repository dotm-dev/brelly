# pipeline/blender/terrain_baker.py
"""Blender script: build tiled terrain meshes from heightmap and export as GLB.

Called by: blender --background --python terrain_baker.py -- <data_json> <out_glb> [texture_path]
data_json: {"width": N, "height": M, "heights": [[...], ...], "cell_size": float}

The heightmap is split into TARGET_TILE_VERTS×TARGET_TILE_VERTS tiles. Each tile becomes
a separate mesh object in the scene, keeping index counts well under WebGL limits.
Adjacent tiles share their border row/column to avoid seams.
UV coordinates always map to the full [0,1] extent so a single SWISSIMAGE texture
covers the whole terrain.
"""
import sys
import json
import os
import math

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

# Maximum vertices per tile side. At 500: each tile has ~1.5M indices — well under WebGL 30M limit.
TARGET_TILE_VERTS = 500

with open(data_json_path) as f:
    data = json.load(f)

heights = data["heights"]
cell    = data["cell_size"]
rows    = len(heights)
cols    = len(heights[0]) if rows else 0

bpy.ops.wm.read_factory_settings(use_empty=True)

# ── Tiling ───────────────────────────────────────────────────────────────────

n_tiles_x = max(1, math.ceil(cols / TARGET_TILE_VERTS))
n_tiles_y = max(1, math.ceil(rows / TARGET_TILE_VERTS))
print(f"Terrain {rows}x{cols} → {n_tiles_y}x{n_tiles_x} tiles", flush=True)


def _build_tile(tx: int, ty: int) -> None:
    """Build one terrain tile and add it to the scene."""
    # Inclusive row/col range for this tile (share border with adjacent tiles)
    c0 = tx * math.ceil(cols / n_tiles_x)
    c1 = min(cols - 1, c0 + math.ceil(cols / n_tiles_x))
    r0 = ty * math.ceil(rows / n_tiles_y)
    r1 = min(rows - 1, r0 + math.ceil(rows / n_tiles_y))

    tile_rows = r1 - r0 + 1
    tile_cols = c1 - c0 + 1

    mesh = bpy.data.meshes.new(f"terrain_{tx}_{ty}")
    bm   = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    verts = []
    for r in range(r0, r1 + 1):
        row_verts = []
        for c in range(c0, c1 + 1):
            x = c * cell - (cols * cell / 2)
            z = r * cell - (rows * cell / 2)
            y = heights[r][c]
            row_verts.append(bm.verts.new((x, z, y)))
        verts.append(row_verts)

    bm.verts.ensure_lookup_table()

    for ri in range(tile_rows - 1):
        for ci in range(tile_cols - 1):
            r_abs = r0 + ri
            c_abs = c0 + ci
            face = bm.faces.new([
                verts[ri][ci],
                verts[ri][ci + 1],
                verts[ri + 1][ci + 1],
                verts[ri + 1][ci],
            ])
            # UV maps to full terrain extent so one texture covers all tiles
            face.loops[0][uv_layer].uv = (c_abs / (cols - 1),         r_abs / (rows - 1))
            face.loops[1][uv_layer].uv = ((c_abs + 1) / (cols - 1),   r_abs / (rows - 1))
            face.loops[2][uv_layer].uv = ((c_abs + 1) / (cols - 1),   (r_abs + 1) / (rows - 1))
            face.loops[3][uv_layer].uv = (c_abs / (cols - 1),         (r_abs + 1) / (rows - 1))

    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new(f"terrain_{tx}_{ty}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


tile_objs = []
for ty in range(n_tiles_y):
    for tx in range(n_tiles_x):
        tile_objs.append(_build_tile(tx, ty))
    print(f"  Row {ty + 1}/{n_tiles_y} built", flush=True)

# ── Material (shared across all tiles) ───────────────────────────────────────

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

    links.new(uv_node.outputs["UV"],     tex_node.inputs["Vector"])
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0

    for obj in tile_objs:
        obj.data.materials.append(mat)
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
print(f"Terrain exported → {out_glb_path} ({n_tiles_y * n_tiles_x} tiles)", flush=True)
