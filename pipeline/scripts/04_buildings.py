#!/usr/bin/env python3
# pipeline/scripts/04_buildings.py
"""Generate buildings.glb from TLM building footprints — pure Python, no Blender."""
import sys, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.io import read_json, ensure_dir, output_dir, progress
from shared.utils.coords import config_from_dict, lv95_to_enu


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
    config = config_from_dict(config_dict)
    out_dir = ensure_dir(output_dir(config_dict))
    out_glb = out_dir / "buildings.glb"

    buildings_data = _load_buildings(out_dir / "reprojected.gpkg", config)
    if not buildings_data:
        print("WARNING: No building data found. Writing placeholder buildings.glb.")
        write_placeholder_glb(out_glb)
        return

    print(f"Writing {len(buildings_data)} buildings → {out_glb}", flush=True)
    write_buildings_glb(buildings_data, out_glb)
    print(f"Buildings GLB → {out_glb}")


# ── GLB writer ────────────────────────────────────────────────────────────────

def _pad4(data: bytes) -> bytes:
    r = len(data) % 4
    return data + b'\x00' * ((4 - r) % 4)


def write_buildings_glb(buildings: list[dict], out_path: Path) -> None:
    import numpy as np

    positions: list[list[float]] = []
    normals:   list[list[float]] = []
    indices:   list[int]         = []

    def _add_face(verts: list[tuple[float, float, float]], normal: tuple[float, float, float]) -> None:
        base = len(positions)
        for v in verts:
            positions.append(list(v))
            normals.append(list(normal))
        # fan triangulation
        for i in range(1, len(verts) - 1):
            indices.extend([base, base + i, base + i + 1])

    for b in buildings:
        fp   = b["footprint"]   # [[east_enu, north_enu], ...]  — glTF Z-negation applied below
        h    = b["height"]
        by   = b["base_y"]
        roof = b["roof"]
        n    = len(fp)
        if n < 3:
            continue

        # Build bottom and top vertex rings.
        # fp is [east_offset, north_offset] from lv95_to_enu.
        # glTF convention for this project: X=east, Y=elevation, Z=-north.
        # Blender's Y-up export applied this negation implicitly; we do it explicitly.
        bottom = [(fp[i][0], by,     -fp[i][1]) for i in range(n)]
        top    = [(fp[i][0], by + h, -fp[i][1]) for i in range(n)]

        # Z-negation flips polygon orientation from CCW (GIS standard) to CW in glTF
        # XZ plane. All face windings must account for this flip.

        # Bottom face: normal (0,-1,0). CW-from-above order gives correct -Y normal.
        _add_face(bottom, (0.0, -1.0, 0.0))

        # Top / roof
        if roof == "pitched" and n >= 4:
            cx = sum(p[0] for p in fp) / n
            cz = -sum(p[1] for p in fp) / n
            w  = max(max(p[0] for p in fp) - min(p[0] for p in fp),
                     max(p[1] for p in fp) - min(p[1] for p in fp))
            ridge_y = by + h + 0.3 * w
            apex = (cx, ridge_y, cz)
            for i in range(n):
                tv0 = top[i]
                tv1 = top[(i + 1) % n]
                # Reversed winding [apex, tv1, tv0] gives outward-facing normals
                # after the Z-flip (verified via cross-product).
                e1 = (tv1[0]-apex[0], tv1[1]-apex[1], tv1[2]-apex[2])
                e2 = (tv0[0]-apex[0], tv0[1]-apex[1], tv0[2]-apex[2])
                nx = e1[1]*e2[2] - e1[2]*e2[1]
                ny_ = e1[2]*e2[0] - e1[0]*e2[2]
                nz = e1[0]*e2[1] - e1[1]*e2[0]
                ln = max((nx**2 + ny_**2 + nz**2) ** 0.5, 1e-9)
                _add_face([apex, tv1, tv0], (nx/ln, ny_/ln, nz/ln))
        else:
            # Top face: normal (0,1,0). Reversed CW = CCW from above gives +Y normal.
            _add_face(list(reversed(top)), (0.0, 1.0, 0.0))

        # Walls: [b0, t0, t1, b1] is CCW when viewed from outside after the Z-flip.
        for i in range(n):
            b0, b1 = bottom[i], bottom[(i + 1) % n]
            t0, t1 = top[i],    top[(i + 1) % n]
            dx, dz = b1[0] - b0[0], b1[2] - b0[2]
            ln = max((dx**2 + dz**2) ** 0.5, 1e-9)
            wn = (dz / ln, 0.0, -dx / ln)
            _add_face([b0, t0, t1, b1], wn)

    if not indices:
        write_placeholder_glb(out_path)
        return

    pos_arr = np.array(positions, dtype=np.float32)
    nor_arr = np.array(normals,   dtype=np.float32)
    idx_arr = np.array(indices,   dtype=np.uint32)

    pos_bytes = pos_arr.tobytes()
    nor_bytes = nor_arr.tobytes()
    idx_bytes = idx_arr.tobytes()

    pos_offset = 0
    nor_offset = len(pos_bytes)
    idx_offset = nor_offset + len(nor_bytes)
    bin_data   = _pad4(pos_bytes + nor_bytes + idx_bytes)

    n_verts = len(positions)
    n_idx   = len(indices)

    pos_min = pos_arr.min(axis=0).tolist()
    pos_max = pos_arr.max(axis=0).tolist()

    gltf = {
        "asset": {"version": "2.0", "generator": "brelly-buildings"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{
            "name": "buildings",
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1},
                "indices": 2,
            }]
        }],
        "accessors": [
            {
                "bufferView": 0, "byteOffset": 0,
                "componentType": 5126, "count": n_verts,
                "type": "VEC3", "min": pos_min, "max": pos_max,
            },
            {
                "bufferView": 1, "byteOffset": 0,
                "componentType": 5126, "count": n_verts,
                "type": "VEC3",
            },
            {
                "bufferView": 2, "byteOffset": 0,
                "componentType": 5125, "count": n_idx,
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": nor_offset, "byteLength": len(nor_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_data)}],
    }

    import json as _json
    json_bytes = _pad4(_json.dumps(gltf, separators=(",", ":")).encode())
    bin_chunk  = _pad4(bin_data)

    chunk0 = struct.pack('<II', len(json_bytes), 0x4E4F534A) + json_bytes
    chunk1 = struct.pack('<II', len(bin_chunk),  0x004E4942) + bin_chunk
    total  = 12 + len(chunk0) + len(chunk1)
    header = struct.pack('<III', 0x46546C67, 2, total)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(header + chunk0 + chunk1)


# ── Data loading ──────────────────────────────────────────────────────────────

def _extract_polygons(geom) -> list:
    name = geom.GetGeometryName().upper()
    if "MULTIPOLYGON" in name:
        return [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
    if "POLYGON" in name:
        return [geom]
    return []


def _load_buildings(gpkg_path: Path, config) -> list[dict]:
    try:
        from osgeo import ogr
        ds = ogr.Open(str(gpkg_path))
        if ds is None:
            return []
        lyr = (ds.GetLayerByName("tlm_bauten_gebaeude_footprint")
               or ds.GetLayerByName("tlm_bb_gebaeude")
               or ds.GetLayerByName("gebaeude"))
        if lyr is None:
            return []
        buildings = []
        total = lyr.GetFeatureCount()
        for j, feat in enumerate(lyr, 1):
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            polys = _extract_polygons(geom)
            for poly in polys:
                ring = poly.GetGeometryRef(0)
                if ring is None:
                    continue
                footprint = []
                elevations = []
                for i in range(ring.GetPointCount()):
                    ex, ny = ring.GetX(i), ring.GetY(i)
                    elev = ring.GetZ(i) if ring.Is3D() else config.base_elevation
                    x, y_elev, z = lv95_to_enu(ex, ny, elev, config)
                    footprint.append([round(x, 2), round(z, 2)])
                    elevations.append(y_elev)
                if len(footprint) >= 3:
                    base_y = round(min(elevations), 2) if elevations else 0.0
                    h_idx = feat.GetFieldIndex("GEBAEUDEHOEHE")
                    raw_h = feat.GetField(h_idx) if h_idx >= 0 else None
                    height = round(float(raw_h), 2) if raw_h and float(raw_h) > 0 else 8.0
                    d_idx = feat.GetFieldIndex("DACHFORM")
                    dachform = (feat.GetField(d_idx) or "") if d_idx >= 0 else ""
                    roof = "pitched" if dachform and "flach" not in dachform.lower() else "flat"
                    buildings.append({
                        "footprint": footprint,
                        "height": height,
                        "base_y": base_y,
                        "roof": roof,
                    })
            if total > 0 and (j % max(1, total // 20) == 0 or j == total):
                progress("loading buildings", j, total)
        return buildings
    except Exception:
        return []


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
