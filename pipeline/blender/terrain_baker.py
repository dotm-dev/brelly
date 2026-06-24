# pipeline/blender/terrain_baker.py
"""Blender script: bake high-res terrain normal map onto low-poly mesh, export GLB.

Called by: blender --background --python terrain_baker.py -- <data_json> <out_glb> [texture_path]
data_json: {"width": N, "height": M, "heights": [[...], ...], "cell_size": float}

Pipeline:
  1. Build high-res mesh from all heights.
  2. Build low-poly mesh by sampling every LOWPOLY_STEP rows/cols.
  3. Bake tangent-space normal map (high -> low) via Cycles CPU.
  4. Apply SWISSIMAGE colour texture + normal map to low-poly material.
  5. Delete high-res mesh. Export low-poly as GLB (normal map embedded).
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

# How many high-res rows/cols to skip per low-poly vertex.
# 8 means low-poly has 1/8 the linear resolution (1/64 the triangles).
LOWPOLY_STEP = 8

# Normal map resolution in pixels. Must be power of 2.
NORMAL_MAP_SIZE = 2048

# Cage extrusion for bake — must be larger than max height delta between
# high-res and low-poly at any point. 4m is conservative for Swiss terrain.
BAKE_CAGE_EXTRUSION = 4.0

# Cap the high-res mesh to at most this many rows/cols to keep bake times sane.
# 4096×4096 = 16.7M vertices; 2048×2048 = 4.2M — still far more than the low-poly.
HIRES_CAP = 2048


with open(data_json_path) as f:
    data = json.load(f)

heights = data["heights"]
cell    = data["cell_size"]
rows    = len(heights)
cols    = len(heights[0]) if rows else 0

bpy.ops.wm.read_factory_settings(use_empty=True)


def _build_terrain_mesh(name, row_step, col_step):
    """Create a Blender mesh object from heights subsampled at the given step."""
    mesh = bpy.data.meshes.new(name)
    bm   = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    sub_rows = list(range(0, rows, row_step))
    sub_cols = list(range(0, cols, col_step))
    if sub_rows[-1] != rows - 1:
        sub_rows.append(rows - 1)
    if sub_cols[-1] != cols - 1:
        sub_cols.append(cols - 1)

    verts = []
    for r in sub_rows:
        row_verts = []
        for c in sub_cols:
            x = c * cell - (cols * cell / 2)
            z = r * cell - (rows * cell / 2)
            y = heights[r][c]
            row_verts.append(bm.verts.new((x, z, y)))
        verts.append(row_verts)

    bm.verts.ensure_lookup_table()
    nr, nc = len(sub_rows), len(sub_cols)

    for ri in range(nr - 1):
        for ci in range(nc - 1):
            r0, c0 = sub_rows[ri],     sub_cols[ci]
            r1, c1 = sub_rows[ri + 1], sub_cols[ci + 1]
            face = bm.faces.new([
                verts[ri][ci],
                verts[ri][ci + 1],
                verts[ri + 1][ci + 1],
                verts[ri + 1][ci],
            ])
            face.loops[0][uv_layer].uv = (c0 / (cols - 1),  r0 / (rows - 1))
            face.loops[1][uv_layer].uv = (c1 / (cols - 1),  r0 / (rows - 1))
            face.loops[2][uv_layer].uv = (c1 / (cols - 1),  r1 / (rows - 1))
            face.loops[3][uv_layer].uv = (c0 / (cols - 1),  r1 / (rows - 1))

    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# Build high-res and low-poly meshes
hires_step = max(1, rows // HIRES_CAP, cols // HIRES_CAP)
hr_rows = max(2, rows // hires_step)
hr_cols = max(2, cols // hires_step)
print(f"Building high-res mesh (~{hr_rows}x{hr_cols})...", flush=True)
hires_obj = _build_terrain_mesh("terrain_hires", row_step=hires_step, col_step=hires_step)

lp_rows = max(2, rows // LOWPOLY_STEP)
lp_cols = max(2, cols // LOWPOLY_STEP)
print(f"Building low-poly mesh (~{lp_rows}x{lp_cols})...", flush=True)
lowpoly_obj = _build_terrain_mesh("terrain", row_step=LOWPOLY_STEP, col_step=LOWPOLY_STEP)


# Bake normal map (high-res -> low-poly)
print("Baking normal map (Cycles CPU)...", flush=True)

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "CPU"
bpy.context.scene.cycles.samples = 1

normal_img = bpy.data.images.new(
    "terrain_normal", width=NORMAL_MAP_SIZE, height=NORMAL_MAP_SIZE,
    float_buffer=True, alpha=False,
)
normal_img.colorspace_settings.name = "Non-Color"

# Low-poly needs a material with the image node ACTIVE for baking target
bake_mat = bpy.data.materials.new("terrain_bake_target")
bake_mat.use_nodes = True
img_node = bake_mat.node_tree.nodes.new("ShaderNodeTexImage")
img_node.image = normal_img
bake_mat.node_tree.nodes.active = img_node
lowpoly_obj.data.materials.append(bake_mat)

# high-res selected (source), low-poly active (target)
bpy.ops.object.select_all(action="DESELECT")
hires_obj.select_set(True)
lowpoly_obj.select_set(True)
bpy.context.view_layer.objects.active = lowpoly_obj

bpy.ops.object.bake(
    type="NORMAL",
    use_selected_to_active=True,
    cage_extrusion=BAKE_CAGE_EXTRUSION,
    normal_space="TANGENT",
)

# Save normal map alongside GLB
normal_map_path = os.path.splitext(out_glb_path)[0] + "_normal.png"
normal_img.filepath_raw = normal_map_path
normal_img.file_format = "PNG"
normal_img.save()
print(f"Normal map saved -> {normal_map_path}", flush=True)

# Remove high-res mesh — no longer needed
bpy.data.objects.remove(hires_obj, do_unlink=True)


# Build final material on low-poly (colour + normal)
lowpoly_obj.data.materials.clear()

mat = bpy.data.materials.new(name="terrain")
mat.use_nodes = True
tree  = mat.node_tree
nodes = tree.nodes
links = tree.links

bsdf = nodes.get("Principled BSDF")

uv_node = nodes.new("ShaderNodeUVMap")
uv_node.uv_map = "UVMap"

# Normal map
nmap_tex  = nodes.new("ShaderNodeTexImage")
nmap_tex.image = normal_img
nmap_tex.image.colorspace_settings.name = "Non-Color"
nmap_node = nodes.new("ShaderNodeNormalMap")
links.new(uv_node.outputs["UV"], nmap_tex.inputs["Vector"])
links.new(nmap_tex.outputs["Color"], nmap_node.inputs["Color"])
links.new(nmap_node.outputs["Normal"], bsdf.inputs["Normal"])

# Colour texture (SWISSIMAGE) if provided
if texture_path:
    col_tex = nodes.new("ShaderNodeTexImage")
    col_tex.image = bpy.data.images.load(os.path.abspath(texture_path))
    col_tex.image.colorspace_settings.name = "sRGB"
    links.new(uv_node.outputs["UV"], col_tex.inputs["Vector"])
    links.new(col_tex.outputs["Color"], bsdf.inputs["Base Color"])
    print(f"Colour texture applied: {texture_path}", flush=True)
else:
    print("No colour texture — exporting untextured terrain", flush=True)

bsdf.inputs["Roughness"].default_value = 1.0
bsdf.inputs["Specular IOR Level"].default_value = 0.0

lowpoly_obj.data.materials.append(mat)


# Export
bpy.ops.export_scene.gltf(
    filepath=out_glb_path,
    export_format="GLB",
    use_selection=False,
    export_image_format="JPEG",
)
print(f"Terrain exported -> {out_glb_path}", flush=True)
