#!/usr/bin/env python3
# pipeline/scripts/02_terrain.py
"""Generate terrain.glb from DEM.

Writes GLB directly (no Blender) so each tile is a guaranteed separate glTF mesh node,
avoiding WebGL index-count limits. TARGET_TILE_VERTS×TARGET_TILE_VERTS tiles at most.
"""
import sys, json, struct, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))                # repo root, for shared/
from shared.utils.io import read_json, ensure_dir, output_dir
from shared.utils.coords import config_from_dict
from scripts._terrain_conform import conform_to_roads

TARGET_TILE_VERTS = 500   # max vertices per tile side; each tile ≤ 3M indices


# ── GLB writer ────────────────────────────────────────────────────────────────

def _pad4(data: bytes) -> bytes:
    r = len(data) % 4
    return data + b'\x00' * ((4 - r) % 4)


def write_terrain_glb(heights, cell: float, texture_path: str | None, out_path: Path,
                      force_tiles: tuple[int, int] | None = None) -> None:
    """Write a tiled terrain GLB directly without Blender."""
    import numpy as np

    heights_np = np.array(heights, dtype=np.float32)
    rows, cols = heights_np.shape

    if force_tiles is not None:
        n_tiles_x, n_tiles_y = force_tiles
    else:
        n_tiles_x = max(1, math.ceil(cols / TARGET_TILE_VERTS))
        n_tiles_y = max(1, math.ceil(rows / TARGET_TILE_VERTS))
    tw = math.ceil(cols / n_tiles_x)   # tile width  in vertices
    th = math.ceil(rows / n_tiles_y)   # tile height in vertices
    print(f"Terrain {rows}×{cols} → {n_tiles_y}×{n_tiles_x} tiles", flush=True)

    # Coordinate convention: match Blender's glTF Y-up export (used by road/building bakers).
    # Blender places verts as (east, north, elevation) then the exporter applies Z-up→Y-up:
    #   glTF_X = east,  glTF_Y = elevation,  glTF_Z = -north
    # So our terrain must also use glTF_Z = -north (Z increases southward).
    # UV V=0 maps to the top of the JPEG (north, GDAL row 0), so V must also be flipped:
    # south vertex (r=0) → V=1, north vertex (r=rows-1) → V=0.

    # Pre-compute smooth normals for the negated-Z convention.
    # Tangent along col: (cell, dh/dc, 0); tangent along row: (0, dh/dr, -cell)
    # Normal = tangent_col × tangent_row = (-dh/dc, cell, +dh/dr)  [note: +dh/dr, not -]
    dh_dc = np.gradient(heights_np, axis=1)
    dh_dr = np.gradient(heights_np, axis=0)
    nx = -dh_dc
    ny = np.ones_like(heights_np) * cell
    nz = +dh_dr                           # positive because Z is negated
    mag = np.sqrt(nx**2 + ny**2 + nz**2)
    nx_n = (nx / mag).astype(np.float32)
    ny_n = (ny / mag).astype(np.float32)
    nz_n = (nz / mag).astype(np.float32)

    # Accumulators for the binary buffer
    bin_parts: list[bytes] = []
    byte_offset = 0

    accessors    = []
    buffer_views = []
    meshes       = []
    nodes        = []

    def _add_buffer_view(data: bytes, target: int | None = None) -> int:
        nonlocal byte_offset
        aligned = _pad4(data)
        bin_parts.append(aligned)
        bv: dict = {"buffer": 0, "byteOffset": byte_offset, "byteLength": len(data)}
        if target is not None:
            bv["target"] = target
        buffer_views.append(bv)
        byte_offset += len(aligned)
        return len(buffer_views) - 1

    ARRAY_BUFFER   = 34962
    ELEMENT_BUFFER = 34963

    for ty in range(n_tiles_y):
        for tx in range(n_tiles_x):
            c0, c1 = tx * tw, min(cols - 1, tx * tw + tw)
            r0, r1 = ty * th, min(rows - 1, ty * th + th)
            tc = c1 - c0 + 1   # tile vertex cols
            tr = r1 - r0 + 1   # tile vertex rows

            # Vertex grid
            r_idx = np.arange(r0, r1 + 1, dtype=np.float32)
            c_idx = np.arange(c0, c1 + 1, dtype=np.float32)
            c_g, r_g = np.meshgrid(c_idx, r_idx)   # (tr, tc)

            x = (c_g * cell - cols * cell / 2).astype(np.float32)
            z = -(r_g * cell - rows * cell / 2).astype(np.float32)   # negate: glTF Z = -north
            y = heights_np[r0:r1+1, c0:c1+1]

            # Positions: glTF (X=east, Y=elevation, Z=-north)
            pos = np.stack([x.ravel(), y.ravel(), z.ravel()], axis=1)  # (n,3)

            # Normals
            nrm = np.stack([
                nx_n[r0:r1+1, c0:c1+1].ravel(),
                ny_n[r0:r1+1, c0:c1+1].ravel(),
                nz_n[r0:r1+1, c0:c1+1].ravel(),
            ], axis=1)  # (n,3)

            # UVs — V flipped so V=0 = north = JPEG row 0 (GDAL convention)
            u = (c_g / max(cols - 1, 1)).astype(np.float32)
            v = (1.0 - r_g / max(rows - 1, 1)).astype(np.float32)   # V=1 south, V=0 north
            uv = np.stack([u.ravel(), v.ravel()], axis=1)   # (n,2)

            # Indices: winding reversed because Z is negated (handedness flip)
            ri = np.arange(tr - 1)
            ci = np.arange(tc - 1)
            ri_g, ci_g = np.meshgrid(ri, ci, indexing='ij')
            a = (ri_g * tc + ci_g).ravel().astype(np.uint32)
            b = a + 1
            c_v = a + tc
            d = c_v + 1
            idx = np.stack([a, b, c_v, b, d, c_v], axis=1).ravel()   # reversed winding

            n_verts = tr * tc
            n_idx   = len(idx)

            # bounding box for accessor min/max
            pos_min = pos.min(axis=0).tolist()
            pos_max = pos.max(axis=0).tolist()

            bv_pos  = _add_buffer_view(pos.tobytes(),  ARRAY_BUFFER)
            bv_nrm  = _add_buffer_view(nrm.tobytes(),  ARRAY_BUFFER)
            bv_uv   = _add_buffer_view(uv.tobytes(),   ARRAY_BUFFER)
            bv_idx  = _add_buffer_view(idx.tobytes(),  ELEMENT_BUFFER)

            acc_pos = len(accessors)
            accessors.append({"bufferView": bv_pos, "componentType": 5126, "count": n_verts, "type": "VEC3",
                               "min": pos_min, "max": pos_max})
            acc_nrm = len(accessors)
            accessors.append({"bufferView": bv_nrm, "componentType": 5126, "count": n_verts, "type": "VEC3"})
            acc_uv  = len(accessors)
            accessors.append({"bufferView": bv_uv,  "componentType": 5126, "count": n_verts, "type": "VEC2"})
            acc_idx = len(accessors)
            accessors.append({"bufferView": bv_idx, "componentType": 5125, "count": n_idx,   "type": "SCALAR"})

            prim = {
                "attributes": {"POSITION": acc_pos, "NORMAL": acc_nrm, "TEXCOORD_0": acc_uv},
                "indices": acc_idx,
                "mode": 4,
            }
            if texture_path:
                prim["material"] = 0

            mesh_idx = len(meshes)
            meshes.append({"name": f"terrain_{tx}_{ty}", "primitives": [prim]})
            nodes.append({"mesh": mesh_idx, "name": f"terrain_{tx}_{ty}"})

        print(f"  Row {ty + 1}/{n_tiles_y} built", flush=True)

    # Optional texture
    materials = []
    textures  = []
    images    = []
    if texture_path and Path(texture_path).exists():
        tex_bytes = Path(texture_path).read_bytes()
        bv_tex = _add_buffer_view(tex_bytes)
        images.append({"bufferView": bv_tex, "mimeType": "image/jpeg"})
        textures.append({"source": 0})
        materials.append({
            "name": "terrain",
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0},
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "doubleSided": True,
        })

    # Assemble binary buffer
    bin_data = b''.join(bin_parts)

    # Build glTF JSON
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "Brelly terrain writer"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }
    if materials: gltf["materials"] = materials
    if textures:  gltf["textures"]  = textures
    if images:    gltf["images"]    = images

    # GLB spec: JSON chunk must be padded with spaces (0x20); BIN chunk with zeros (0x00)
    json_raw  = json.dumps(gltf, separators=(',', ':')).encode()
    json_pad  = b' ' * ((4 - len(json_raw) % 4) % 4)
    json_full = json_raw + json_pad                                # total 4-aligned

    bin_pad   = b'\x00' * ((4 - len(bin_data) % 4) % 4)
    bin_full  = bin_data + bin_pad

    json_chunk     = struct.pack('<II', len(json_full), 0x4E4F534A) + json_full
    bin_chunk_full = (struct.pack('<II', len(bin_full), 0x004E4942) + bin_full) if bin_full else b''
    total = 12 + len(json_chunk) + len(bin_chunk_full)
    header = struct.pack('<III', 0x46546C67, 2, total)

    out_path.write_bytes(header + json_chunk + bin_chunk_full)
    tiles = n_tiles_x * n_tiles_y
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"Terrain GLB → {out_path}  ({tiles} tiles, {size_mb:.1f} MB)", flush=True)


# ── Pipeline entry ────────────────────────────────────────────────────────────

def write_placeholder_glb(path: Path) -> None:
    json_content = b'{"asset":{"version":"2.0"}}'
    padding = (4 - len(json_content) % 4) % 4
    json_content += b' ' * padding
    chunk0 = struct.pack('<II', len(json_content), 0x4E4F534A) + json_content
    total = 12 + len(chunk0)
    header = struct.pack('<III', 0x46546C67, 2, total)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + chunk0)


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    out_dir = ensure_dir(output_dir(config_dict))
    out_glb = out_dir / "terrain.glb"

    data = _load_or_synthesize_heightmap(config_dict)
    # Base texture size on physical extent, not heightmap vert count (which may be capped).
    # Texture is saved as a separate file — not embedded in the GLB — so the GLB stays lean
    # and there's no 4096 WebGL embed limit to worry about.
    from shared.utils.coords import config_from_dict as _cfg
    import shutil
    _c = _cfg(config_dict)
    tex_size = min(8192, max(int(_c.radius_m * 2 / 1.75), 2048))
    texture_path = _fetch_swissimage(config_dict, out_dir, tex_size=tex_size)
    terrain_texture_out = out_dir / "terrain_texture.jpg"
    if texture_path and Path(texture_path).exists():
        shutil.copy2(texture_path, terrain_texture_out)
    try:
        write_terrain_glb(data["heights"], data["cell_size"], None, out_glb)
    except Exception as e:
        import traceback
        print(f"ERROR: write_terrain_glb failed: {e}")
        traceback.print_exc()
        write_placeholder_glb(out_glb)


def _refresh_vrt(vrt_path: Path, gdal) -> None:
    """Rebuild VRT from all .tif files in the same directory, so terrain always uses current tiles."""
    data_dir = vrt_path.parent
    tif_files = sorted(str(p) for p in data_dir.glob("*.tif"))
    if not tif_files:
        return
    vrt_opts = gdal.BuildVRTOptions(resampleAlg="nearest")
    ds = gdal.BuildVRT(str(vrt_path), tif_files, options=vrt_opts)
    if ds is not None:
        ds.FlushCache()
        print(f"  VRT refreshed ({len(tif_files)} tiles)", flush=True)


def _load_or_synthesize_heightmap(config_dict: dict) -> dict:
    cell_size = float(config_dict.get("terrain_cell_m", 1.0))
    fallback_size = 64
    try:
        from osgeo import gdal
        import numpy as np
        from shared.utils.coords import bbox_from_center
        gdal.UseExceptions()
        config = config_from_dict(config_dict)
        dem_path = config_dict["source_data"].get("dem", "")
        if not Path(dem_path).exists():
            raise FileNotFoundError(dem_path)

        _refresh_vrt(Path(dem_path), gdal)

        bbox = bbox_from_center(config)
        diameter = config.radius_m * 2
        n_cells = max(64, int(diameter / cell_size))
        # Cap to avoid exceeding GLB uint32 size limit (~4GB binary).
        # With 1400 verts per side: ~2M verts × 56 bytes = ~112MB binary, safe for WebGL.
        MAX_VERTS = 1400
        if n_cells > MAX_VERTS:
            print(f"  Capping terrain from {n_cells}×{n_cells} to {MAX_VERTS}×{MAX_VERTS} verts", flush=True)
            n_cells = MAX_VERTS
        actual_cell = diameter / n_cells

        NODATA_SENTINEL = -9999.0
        ds = gdal.Open(dem_path)
        mem_ds = gdal.Warp(
            '', ds,
            format='MEM',
            outputBounds=(bbox['min_e'], bbox['min_n'], bbox['max_e'], bbox['max_n']),
            width=n_cells, height=n_cells,
            resampleAlg='bilinear',
            dstNodata=NODATA_SENTINEL,
        )
        band = mem_ds.GetRasterBand(1)
        band.SetNoDataValue(NODATA_SENTINEL)

        # Fill cells outside the Swiss DEM coverage (nodata) by nearest-neighbor
        # propagation so the terrain doesn't drop to y=0 at boundaries.
        gdal.FillNodata(band, None, maxSearchDist=200, smoothingIterations=2)

        arr = band.ReadAsArray().astype(float)
        # Any remaining unfilled sentinel cells (very large gaps): clamp to base_elevation
        arr[arr == NODATA_SENTINEL] = config.base_elevation
        arr -= config.base_elevation
        arr = np.flipud(arr)

        road_segments, n_splines = _smooth_and_save_splines(config_dict, bbox, config, ds)
        if road_segments:
            conform_to_roads(
                arr, road_segments,
                min_e=bbox["min_e"], min_n=bbox["min_n"],
                cell_size=actual_cell, blend_cells=2,
            )
            print(f"  Road cut/fill: {len(road_segments)} ground segments "
                  f"from {n_splines} splines", flush=True)

        return {"width": n_cells, "height": n_cells, "heights": arr.tolist(), "cell_size": actual_cell}
    except Exception as e:
        print(f"WARNING: Could not load DEM ({e}). Using flat heightmap.")
        heights = [[0.0] * fallback_size for _ in range(fallback_size)]
        return {"width": fallback_size, "height": fallback_size, "heights": heights, "cell_size": cell_size}


def _smooth_and_save_splines(config_dict: dict, bbox: dict, config, dem_ds) -> tuple[list, int]:
    """Run intersection locking + Laplacian smoothing on TLM roads.

    Saves road_splines.json to the output directory for consumption by 03_roads.py
    and Babylon.js.  Returns (road_segments, n_splines) where road_segments are
    the ground-only RoadSegment objects ready for cut/fill terrain deformation.
    """
    try:
        import json as _json
        from osgeo import ogr
        from shared.utils.io import output_dir
        from scripts.road_graph import RoadLine
        from scripts._road_smoother import smooth_roads

        gpkg = output_dir(config_dict) / "reprojected.gpkg"
        if not gpkg.exists():
            return [], 0

        ogr_ds = ogr.Open(str(gpkg))
        if ogr_ds is None:
            return [], 0
        lyr = ogr_ds.GetLayerByName("tlm_strassen_strasse") or ogr_ds.GetLayer(0)
        if lyr is None:
            return [], 0

        _OBJEKTART_MAP = {
            "Autobahn":    ("road_major", 14.0), "Autostrasse":  ("road_major", 12.0),
            "10m Strasse": ("road_major", 10.0), "8m Strasse":   ("road_major",  8.0),
            "6m Strasse":  ("road_main",   6.0), "4m Strasse":   ("road_local",  4.0),
            "3m Strasse":  ("road_small",  3.0), "Verbindung":   ("road_local",  4.0),
            "Einfahrt":    ("road_small",  3.0), "Ausfahrt":     ("road_small",  3.0),
            "Zufahrt":     ("road_small",  3.0), "Dienstzufahrt":("road_small",  2.5),
            "Raststaette": ("road_local",  4.0), "2m Weg":       ("path",        2.0),
            "2m Wegfragment": ("path", 2.0),     "1m Weg":       ("path",        1.5),
            "1m Wegfragment": ("path", 1.5),     "Markierte Spur":("path",       1.5),
        }
        _SKIP = {"Platz", "Klettersteig", "Faehre", "Autozug"}

        lyr.SetSpatialFilterRect(bbox["min_e"], bbox["min_n"], bbox["max_e"], bbox["max_n"])
        defn = lyr.GetLayerDefn()
        obj_idx = defn.GetFieldIndex("OBJEKTART")
        base_elev = config.base_elevation

        roads: list[RoadLine] = []
        for feat in lyr:
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            raw = feat.GetField(obj_idx) if obj_idx >= 0 else None
            if raw in _SKIP:
                continue
            road_type, width_m = _OBJEKTART_MAP.get(raw, ("road_local", 4.0))
            coords = [
                (geom.GetX(i), geom.GetY(i),
                 geom.GetZ(i) if geom.Is3D() else base_elev)
                for i in range(geom.GetPointCount())
            ]
            if len(coords) >= 2:
                roads.append(RoadLine(id=str(feat.GetFID()), coords_lv95=coords,
                                      width_m=width_m, road_type=road_type))

        if not roads:
            return [], 0

        spline_dicts, road_segments = smooth_roads(roads, config, dem_ds)

        # Save spline JSON for 03_roads.py and Babylon.js ribbon extrusion.
        out_json = output_dir(config_dict) / "road_splines.json"
        out_json.write_text(_json.dumps(spline_dicts, separators=(',', ':')))
        print(f"  Splines saved → {out_json}  ({len(spline_dicts)} roads)", flush=True)

        return road_segments, len(spline_dicts)

    except Exception as e:
        import traceback
        print(f"  WARNING: road smoothing skipped ({e})", flush=True)
        traceback.print_exc()
        return [], 0


def _fetch_swissimage(config_dict: dict, out_dir: Path, tex_size: int = 1024) -> str | None:
    try:
        from shared.utils.coords import config_from_dict
        config = config_from_dict(config_dict)
    except Exception:
        return None

    out_path = out_dir / f"_terrain_texture_{config.radius_m:.0f}.jpg"
    if out_path.exists():
        print(f"SWISSIMAGE texture cached → {out_path}")
        return str(out_path)

    try:
        from osgeo import gdal
        from shared.utils.coords import bbox_from_center
        gdal.UseExceptions()

        bbox = bbox_from_center(config)

        wms_xml = (
            "<GDAL_WMS><Service name=\"TMS\">"
            "<ServerUrl>https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage"
            "/default/current/3857/${z}/${x}/${y}.jpeg</ServerUrl>"
            "</Service>"
            "<DataWindow>"
            "<UpperLeftX>-20037508.34</UpperLeftX><UpperLeftY>20037508.34</UpperLeftY>"
            "<LowerRightX>20037508.34</LowerRightX><LowerRightY>-20037508.34</LowerRightY>"
            "<TileLevel>18</TileLevel>"
            "<TileCountX>1</TileCountX><TileCountY>1</TileCountY>"
            "<YOrigin>top</YOrigin>"
            "</DataWindow>"
            "<Projection>EPSG:3857</Projection>"
            "<BlockSizeX>256</BlockSizeX><BlockSizeY>256</BlockSizeY>"
            "<BandsCount>3</BandsCount>"
            "<Cache/>"
            "</GDAL_WMS>"
        )

        print("Fetching SWISSIMAGE orthophoto…", flush=True)
        wms_ds = gdal.Open(wms_xml)
        if wms_ds is None:
            raise RuntimeError("Could not open WMTS source")

        mem_ds = gdal.Warp(
            "",
            wms_ds,
            format="MEM",
            outputBounds=(bbox["min_e"], bbox["min_n"], bbox["max_e"], bbox["max_n"]),
            outputBoundsSRS="EPSG:2056",
            dstSRS="EPSG:2056",
            width=tex_size,
            height=tex_size,
            resampleAlg="bilinear",
        )
        if mem_ds is None:
            raise RuntimeError("Warp returned empty dataset")

        import numpy as np_tex
        # Fill pixels where WMTS returned no data (black, outside Switzerland coverage)
        # with a neutral mid-green so border areas don't appear as dark voids.
        arr_r = mem_ds.GetRasterBand(1).ReadAsArray()
        arr_g = mem_ds.GetRasterBand(2).ReadAsArray()
        arr_b = mem_ds.GetRasterBand(3).ReadAsArray()
        mask_empty = (arr_r.astype(np_tex.int16) + arr_g + arr_b) < 15   # near-black = nodata
        if mask_empty.any():
            arr_r[mask_empty] = 110
            arr_g[mask_empty] = 130
            arr_b[mask_empty] = 85
            mem_ds.GetRasterBand(1).WriteArray(arr_r)
            mem_ds.GetRasterBand(2).WriteArray(arr_g)
            mem_ds.GetRasterBand(3).WriteArray(arr_b)

        gdal.GetDriverByName("JPEG").CreateCopy(str(out_path), mem_ds, options=["QUALITY=85"])
        mem_ds = None
        print(f"SWISSIMAGE texture → {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"WARNING: Could not fetch SWISSIMAGE ({e}). Terrain will be untextured.")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
