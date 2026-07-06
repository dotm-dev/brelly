#!/usr/bin/env python3
# pipeline/scripts/03_roads.py
"""Generate roads.glb from TLM road vectors — pure Python, no Blender."""
import re
import sys, struct, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.io import read_json, ensure_dir, output_dir, progress
from shared.utils.coords import config_from_dict, lv95_to_enu, bbox_from_center
from shared.utils.constants import ROAD_LIFT, MAX_ROAD_MITER
from scripts.road_graph import RoadLine
from scripts._road_resampler import _resample_nodes


def write_placeholder_glb(path: Path) -> None:
    json_content = b'{"asset":{"version":"2.0"}}'
    padding = (4 - len(json_content) % 4) % 4
    json_content += b' ' * padding
    chunk0 = struct.pack('<II', len(json_content), 0x4E4F534A) + json_content
    total = 12 + len(chunk0)
    header = struct.pack('<III', 0x46546C67, 2, total)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + chunk0)


# ── Miter-joint road mesh builder ────────────────────────────────────────────

def _norm2(dx: float, dz: float) -> tuple[float, float]:
    """Normalize a 2-D vector (East, North)."""
    mag = math.sqrt(dx * dx + dz * dz)
    if mag < 1e-6:
        return 0.0, 0.0
    return dx / mag, dz / mag


def _miter_perp(pts_enu: list[tuple[float, float, float]], i: int, half_w: float
                ) -> tuple[float, float]:
    """Miter-corrected lateral offset in ENU XZ (East, North) plane at point i.

    Works entirely in the East-North plane; elevation is handled separately.
    Returns (delta_east, delta_north) for the right-side offset.
    """
    n = len(pts_enu)

    def safe_dir(a, b):
        dx = b[0] - a[0]
        dz = b[2] - a[2]
        nx, nz = _norm2(dx, dz)
        return (nx, nz) if (nx != 0 or nz != 0) else None

    if i == 0:
        d = safe_dir(pts_enu[0], pts_enu[1]) or (1.0, 0.0)
        d_in = d_out = d
    elif i == n - 1:
        d = safe_dir(pts_enu[n - 2], pts_enu[n - 1]) or (1.0, 0.0)
        d_in = d_out = d
    else:
        d_in  = safe_dir(pts_enu[i - 1], pts_enu[i])
        d_out = safe_dir(pts_enu[i],     pts_enu[i + 1])
        if d_in is None and d_out is None:
            d_in = d_out = (1.0, 0.0)
        elif d_in is None:
            d_in = d_out
        elif d_out is None:
            d_out = d_in

    # Bisector (East, North)
    bx = d_in[0] + d_out[0]
    bz = d_in[1] + d_out[1]
    bx, bz = _norm2(bx, bz)
    if bx == 0 and bz == 0:
        bx, bz = d_out

    # Miter perpendicular (rotate bisector 90° right): (bz, -bx) in (East, North)
    mx, mz = bz, -bx

    # Miter scale capped by MAX_MITER
    out_perp_x, out_perp_z = d_out[1], -d_out[0]   # right-perpendicular of d_out
    dot = mx * out_perp_x + mz * out_perp_z
    cos_a = abs(dot)
    scale = 1.0 / max(cos_a, 1.0 / MAX_ROAD_MITER)

    return mx * half_w * scale, mz * half_w * scale


def _sample_dem(dem_ds, e: float, n: float, fallback: float) -> float:
    """Return DEM elevation (absolute metres) at LV95 (e, n), or fallback on miss."""
    if dem_ds is None:
        return fallback
    try:
        gt = dem_ds.GetGeoTransform()
        col = (e - gt[0]) / gt[1]
        row = (n - gt[3]) / gt[5]
        col_i, row_i = int(col), int(row)
        w, h = dem_ds.RasterXSize, dem_ds.RasterYSize
        if not (0 <= col_i < w and 0 <= row_i < h):
            return fallback
        val = float(dem_ds.GetRasterBand(1).ReadAsArray(col_i, row_i, 1, 1)[0][0])
        nodata = dem_ds.GetRasterBand(1).GetNoDataValue()
        if nodata is not None and abs(val - nodata) < 1:
            return fallback
        return val
    except Exception:
        return fallback


def _build_road_meshes(roads: list[RoadLine], config, dem_ds=None
                       ) -> dict[str, tuple[list, list]]:
    """Return {road_type: (positions, indices)} in glTF space (X=East, Y=elev, Z=-North).

    Each edge vertex samples the DEM at its own LV95 position so roads follow
    the terrain cross-section on slopes instead of clipping through it.
    """
    from collections import defaultdict
    meshes: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))

    for road in roads:
        if len(road.coords_lv95) < 2:
            continue

        # Keep raw LV95 coords alongside ENU so we can sample DEM at edge positions.
        lv95_pts = road.coords_lv95                        # [(e, n, abs_elev), ...]
        pts_enu  = [lv95_to_enu(e, n, elev, config) for e, n, elev in lv95_pts]
        half_w   = road.width_m / 2.0

        left_pts:  list[tuple[float, float, float]] = []
        right_pts: list[tuple[float, float, float]] = []

        for i, ((e_lv95, n_lv95, abs_elev), (ex, _ey, en)) in enumerate(
                zip(lv95_pts, pts_enu)):
            de, dn = _miter_perp(pts_enu, i, half_w)

            # LV95 positions of the left and right edge (East/North offsets in metres)
            left_e,  left_n  = e_lv95 - de, n_lv95 - dn
            right_e, right_n = e_lv95 + de, n_lv95 + dn

            # Sample DEM at each edge independently so roads hug the terrain cross-section.
            # Use max(DEM_at_edge, TLM_centerline) so roads are never below the terrain
            # that conform_to_roads raised to TLM elevation around the road corridor.
            left_abs  = max(_sample_dem(dem_ds, left_e,  left_n,  abs_elev), abs_elev)
            right_abs = max(_sample_dem(dem_ds, right_e, right_n, abs_elev), abs_elev)

            left_y  = (left_abs  - config.base_elevation) + ROAD_LIFT
            right_y = (right_abs - config.base_elevation) + ROAD_LIFT

            # glTF convention: X=East, Y=elevation, Z=-North
            left_pts.append( (ex - de, left_y,  -(en - dn)) )
            right_pts.append((ex + de, right_y, -(en + dn)) )

        positions, indices = meshes[road.road_type]
        base = len(positions)
        for lp, rp in zip(left_pts, right_pts):
            positions.append(lp)
            positions.append(rp)

        n_segs = len(pts_enu) - 1
        for s in range(n_segs):
            l0 = base + s * 2
            r0 = l0 + 1
            l1 = l0 + 2
            r1 = l0 + 3
            # Two triangles (CCW winding in glTF right-handed Y-up)
            indices.extend([l0, r0, l1, r0, r1, l1])

    return dict(meshes)


def _build_road_meshes_from_splines(spline_dicts: list[dict]) -> dict[str, tuple[list, list]]:
    """Build {road_type: (positions, indices)} from pre-smoothed spline dicts.

    Nodes are already in glTF space (X=East, Y=local_elev, Z=−North).
    Bridge/tunnel segments get a small Y lift so they clear the terrain surface.
    """
    from collections import defaultdict
    BRIDGE_LIFT = 0.3   # metres above baked terrain for bridge ribbon

    meshes: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))

    for spline in spline_dicts:
        road_type = spline["roadType"]
        half_w    = spline["widthMetres"] / 2.0
        nodes     = spline["nodes"]       # [{"x", "y", "z", "isLocked"}, ...]
        segments  = spline["segments"]    # [{"startIdx", "endIdx", "kind"}, ...]

        nodes, segments = _resample_nodes(nodes, segments)

        n_pts = len(nodes)
        if n_pts < 2:
            continue

        # Build per-node Y lift: bridge nodes get BRIDGE_LIFT.
        node_lift = [0.0] * n_pts
        for seg in segments:
            if seg["kind"] == "bridge":
                node_lift[seg["startIdx"]] = BRIDGE_LIFT
                node_lift[seg["endIdx"]]   = BRIDGE_LIFT

        # Post-resample Y smoothing: resampler does linear interpolation between
        # original TLM nodes, leaving slope kinks at every source-node boundary.
        # A few Laplacian passes on the resampled Y values eliminate those kinks.
        _POST_ITERS  = 20
        _POST_ALPHA  = 0.5
        locked = [nd["isLocked"] for nd in nodes]
        ys = [nd["y"] for nd in nodes]
        for _ in range(_POST_ITERS):
            new_ys = ys[:]
            for i in range(1, n_pts - 1):
                if not locked[i]:
                    new_ys[i] = ys[i] + _POST_ALPHA * (ys[i-1] - 2*ys[i] + ys[i+1])
            ys = new_ys

        # _miter_perp expects (East, elev, North) — index 0=East, 2=North.
        # Spline nodes use glTF convention where Z=−North, so negate Z for miter calc.
        pts_gltf   = [(nd["x"], ys[i] + node_lift[i] + ROAD_LIFT, nd["z"]) for i, nd in enumerate(nodes)]
        pts_miter  = [(nd["x"], nd["y"],                -nd["z"]) for nd in nodes]

        left_pts:  list[tuple[float, float, float]] = []
        right_pts: list[tuple[float, float, float]] = []

        for i, pt in enumerate(pts_gltf):
            de, dn = _miter_perp(pts_miter, i, half_w)
            # de = East offset, dn = North offset → glTF Z offset = −dn
            left_pts.append( (pt[0] - de, pt[1], pt[2] + dn) )
            right_pts.append((pt[0] + de, pt[1], pt[2] - dn) )

        positions, indices = meshes[road_type]
        base = len(positions)
        for lp, rp in zip(left_pts, right_pts):
            positions.append(lp)
            positions.append(rp)

        for s in range(n_pts - 1):
            l0 = base + s * 2
            r0 = l0 + 1
            l1 = l0 + 2
            r1 = l0 + 3
            indices.extend([l0, r0, l1, r0, r1, l1])

    return dict(meshes)


# ── glTF / GLB writer ─────────────────────────────────────────────────────────

def _pad4(data: bytes) -> bytes:
    r = len(data) % 4
    return data + b'\x00' * ((4 - r) % 4)


_TYPE_COLOR = {
    "road_major": (0.20, 0.20, 0.24),
    "road_main":  (0.25, 0.25, 0.28),
    "road_local": (0.30, 0.30, 0.33),
    "road_small": (0.35, 0.35, 0.37),
    "path":       (0.45, 0.40, 0.35),
}


def write_roads_glb(road_meshes: dict, out_path: Path) -> None:
    import numpy as np

    bin_parts: list[bytes] = []
    byte_offset = 0
    buffer_views = []
    accessors    = []
    meshes_json  = []
    materials    = []
    nodes        = []

    ARRAY_BUFFER   = 34962
    ELEMENT_BUFFER = 34963

    def _add_bv(data: bytes, target: int | None = None) -> int:
        nonlocal byte_offset
        aligned = _pad4(data)
        bin_parts.append(aligned)
        bv: dict = {"buffer": 0, "byteOffset": byte_offset, "byteLength": len(data)}
        if target is not None:
            bv["target"] = target
        buffer_views.append(bv)
        byte_offset += len(aligned)
        return len(buffer_views) - 1

    for road_type, (positions, indices) in road_meshes.items():
        if not positions or not indices:
            continue

        pos_arr = np.array(positions, dtype=np.float32)
        idx_arr = np.array(indices,   dtype=np.uint32)

        pos_min = pos_arr.min(axis=0).tolist()
        pos_max = pos_arr.max(axis=0).tolist()

        bv_pos = _add_bv(pos_arr.tobytes(), ARRAY_BUFFER)
        bv_idx = _add_bv(idx_arr.tobytes(), ELEMENT_BUFFER)

        acc_pos = len(accessors)
        accessors.append({
            "bufferView": bv_pos, "componentType": 5126, "count": len(positions),
            "type": "VEC3", "min": pos_min, "max": pos_max,
        })
        acc_idx = len(accessors)
        accessors.append({
            "bufferView": bv_idx, "componentType": 5125, "count": len(indices),
            "type": "SCALAR",
        })

        mat_idx = len(materials)
        r, g, b = _TYPE_COLOR.get(road_type, (0.3, 0.3, 0.3))
        materials.append({
            "name": road_type,
            "pbrMetallicRoughness": {
                "baseColorFactor": [r, g, b, 1.0],
                "metallicFactor":  0.0,
                "roughnessFactor": 1.0,
            },
            "doubleSided": True,
        })

        mesh_idx = len(meshes_json)
        meshes_json.append({
            "name": road_type,
            "primitives": [{
                "attributes": {"POSITION": acc_pos},
                "indices": acc_idx,
                "material": mat_idx,
                "mode": 4,
            }],
        })
        nodes.append({"mesh": mesh_idx, "name": road_type})

    if not nodes:
        write_placeholder_glb(out_path)
        return

    bin_data = b''.join(bin_parts)

    gltf: dict = {
        "asset": {"version": "2.0", "generator": "brelly-roads"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes_json,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }

    json_raw  = json.dumps(gltf, separators=(',', ':')).encode()
    json_pad  = b' ' * ((4 - len(json_raw) % 4) % 4)
    json_full = json_raw + json_pad

    bin_pad   = b'\x00' * ((4 - len(bin_data) % 4) % 4)
    bin_full  = bin_data + bin_pad

    json_chunk = struct.pack('<II', len(json_full), 0x4E4F534A) + json_full
    bin_chunk  = (struct.pack('<II', len(bin_full), 0x004E4942) + bin_full) if bin_full else b''
    total = 12 + len(json_chunk) + len(bin_chunk)
    header = struct.pack('<III', 0x46546C67, 2, total)

    out_path.write_bytes(header + json_chunk + bin_chunk)


# ── Pipeline entry ─────────────────────────────────────────────────────────────

import json   # needed for write_roads_glb


def _open_dem(config_dict: dict):
    """Return an open GDAL dataset for the DEM, or None."""
    try:
        from osgeo import gdal
        gdal.UseExceptions()
        dem_path = config_dict.get("source_data", {}).get("dem", "")
        if dem_path and Path(dem_path).exists():
            return gdal.Open(dem_path)
    except Exception:
        pass
    return None


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    config = config_from_dict(config_dict)
    out_dir = ensure_dir(output_dir(config_dict))
    out_glb = out_dir / "roads.glb"

    splines_path = out_dir / "road_splines.json"
    if splines_path.exists():
        # Fast path: 02_terrain already smoothed the roads — build mesh from those.
        print(f"Building road meshes from smoothed splines…", flush=True)
        with open(splines_path) as f:
            spline_dicts = json.load(f)
        road_meshes = _build_road_meshes_from_splines(spline_dicts)
    else:
        # Fallback: raw TLM data (no smoothing — pre-run 02_terrain first for best results).
        print("WARNING: road_splines.json not found — using raw TLM data.", flush=True)
        bbox = bbox_from_center(config)
        roads = _load_roads(out_dir / "reprojected.gpkg", bbox)
        if not roads:
            print("WARNING: No road data found. Writing placeholder roads.glb.")
            write_placeholder_glb(out_glb)
            return
        dem_ds = _open_dem(config_dict)
        road_meshes = _build_road_meshes(roads, config, dem_ds)

    write_roads_glb(road_meshes, out_glb)
    n_verts = sum(len(p) for p, _ in road_meshes.values())
    print(f"Roads GLB → {out_glb}  ({len(road_meshes)} types, {n_verts} vertices)")


# ── Road data loading ─────────────────────────────────────────────────────────

_OBJEKTART_MAP = {
    "Autobahn":       ("road_major", 14.0),
    "Autostrasse":    ("road_major", 12.0),
    "10m Strasse":    ("road_major", 10.0),
    "8m Strasse":     ("road_major",  8.0),
    "6m Strasse":     ("road_main",   6.0),
    "4m Strasse":     ("road_local",  4.0),
    "3m Strasse":     ("road_small",  3.0),
    "Verbindung":     ("road_local",  4.0),
    "Einfahrt":       ("road_small",  3.0),
    "Ausfahrt":       ("road_small",  3.0),
    "Zufahrt":        ("road_small",  3.0),
    "Dienstzufahrt":  ("road_small",  2.5),
    "Raststaette":    ("road_local",  4.0),
    "2m Weg":         ("path",        2.0),
    "2m Wegfragment": ("path",        2.0),
    "1m Weg":         ("path",        1.5),
    "1m Wegfragment": ("path",        1.5),
    "Markierte Spur": ("path",        1.5),
    # Non-road features — skip
    "Platz":          None,
    "Klettersteig":   None,
    "Faehre":         None,
    "Autozug":        None,
}

def _parse_objektart(raw: str) -> tuple[str, float] | None:
    if raw and raw in _OBJEKTART_MAP:
        return _OBJEKTART_MAP[raw]
    m = re.match(r"(\d+(?:\.\d+)?)m", raw or "")
    width = float(m.group(1)) if m else 4.0
    road_type = "path" if "Weg" in (raw or "") else "road_local"
    return road_type, width


def _load_roads(gpkg_path: Path, bbox: dict | None = None) -> list[RoadLine]:
    try:
        from osgeo import ogr
        ds = ogr.Open(str(gpkg_path))
        if ds is None:
            return []
        lyr = ds.GetLayerByName("tlm_strassen_strasse") or ds.GetLayer(0)
        if lyr is None:
            return []
        if bbox:
            lyr.SetSpatialFilterRect(bbox["min_e"], bbox["min_n"],
                                     bbox["max_e"], bbox["max_n"])
        roads = []
        total = lyr.GetFeatureCount()
        obj_idx = -1
        for j, feat in enumerate(lyr, 1):
            if j == 1:
                obj_idx = feat.GetFieldIndex("OBJEKTART")
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            raw_obj = feat.GetField(obj_idx) if obj_idx >= 0 else None
            parsed = _parse_objektart(raw_obj)
            if parsed is None:
                continue
            road_type, width_m = parsed
            coords = [(geom.GetX(i), geom.GetY(i), geom.GetZ(i) if geom.Is3D() else 0.0)
                      for i in range(geom.GetPointCount())]
            roads.append(RoadLine(id=str(feat.GetFID()), coords_lv95=coords,
                                  width_m=width_m, road_type=road_type))
            if total > 0 and (j % max(1, total // 20) == 0 or j == total):
                progress("loading roads", j, total)
        return roads
    except Exception:
        return []


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
