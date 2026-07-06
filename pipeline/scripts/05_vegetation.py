#!/usr/bin/env python3
# pipeline/scripts/05_vegetation.py
"""Extract tree positions from TLM and write vegetation.glb — pure Python, no Blender."""
import math, random, sys, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))                # repo root, for shared/
from shared.utils.io import read_json, write_json, output_dir, progress
from shared.utils.coords import config_from_dict, lv95_to_enu, bbox_from_center
from shared.utils.constants import TREE_LIFT, TREE_HEIGHT, TREE_RADIUS, TREE_SIDES

# Target trees scattered into forest polygons (globally capped)
FOREST_TREE_BUDGET = 12_000
MAX_TREES_PER_HA = 80   # per-polygon density cap — prevents one large polygon consuming the whole budget
FOREST_TYPES = {"Wald", "Gehoelzflaeche", "Gebueschwald"}
RANDOM_SEED = 42


def _scatter_in_polygon(geom, n_trees: int, base_elevation: float) -> list[tuple]:
    from osgeo import ogr
    """Return up to n_trees random LV95 (e, n, elev) points inside geom."""
    env = geom.GetEnvelope()   # (min_e, max_e, min_n, max_n)
    min_e, max_e, min_n, max_n = env
    area = geom.GetArea()
    spacing = math.sqrt(area / n_trees) * 0.8
    spacing = max(spacing, 5.0)

    pts = []
    e = min_e + random.uniform(0, spacing)
    while e < max_e:
        n = min_n + random.uniform(0, spacing)
        while n < max_n:
            jitter_e = random.uniform(-spacing * 0.35, spacing * 0.35)
            jitter_n = random.uniform(-spacing * 0.35, spacing * 0.35)
            test_e, test_n = e + jitter_e, n + jitter_n
            pt = ogr.CreateGeometryFromWkt(f"POINT ({test_e} {test_n})")
            if geom.Contains(pt):
                pts.append((test_e, test_n, base_elevation))
            n += spacing
        e += spacing
    return pts


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


def _sample_dem(dem_ds, e: float, n: float, fallback: float) -> float:
    """Return DEM elevation at LV95 (e, n), or fallback on miss."""
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
        val = dem_ds.GetRasterBand(1).ReadAsArray(col_i, row_i, 1, 1)[0][0]
        nodata = dem_ds.GetRasterBand(1).GetNoDataValue()
        if nodata is not None and abs(val - nodata) < 1:
            return fallback
        return float(val)
    except Exception:
        return fallback


# ── GLB writer ────────────────────────────────────────────────────────────────

def _pad4(data: bytes) -> bytes:
    r = len(data) % 4
    return data + b'\x00' * ((4 - r) % 4)


def write_vegetation_glb(positions: list[dict], out_path: Path) -> None:
    """Write cone trees at given ENU positions directly to a GLB file.

    positions: list of {"x": East_offset, "y": elev_offset, "z": North_offset}
    glTF convention: X=East, Y=elevation, Z=-North.
    """
    import numpy as np

    all_positions: list[tuple] = []
    all_indices:   list[int]   = []

    for pos in positions:
        east  = pos["x"]
        elev  = pos["y"] + TREE_LIFT   # lift roots slightly off terrain surface
        north = pos["z"]

        # In glTF: X=East, Y=elevation, Z=-North
        gx = east
        gy = elev
        gz = -north

        base_idx = len(all_positions)

        # Tip vertex
        all_positions.append((gx, gy + TREE_HEIGHT, gz))

        # Ring vertices at base
        for i in range(TREE_SIDES):
            angle = 2 * math.pi * i / TREE_SIDES
            all_positions.append((
                gx + TREE_RADIUS * math.cos(angle),
                gy,
                gz + TREE_RADIUS * math.sin(angle),
            ))

        tip  = base_idx
        ring = [base_idx + 1 + i for i in range(TREE_SIDES)]

        # Side triangles (tip, ring[i+1], ring[i]) — CCW from outside in glTF Y-up
        for i in range(TREE_SIDES):
            a = ring[i]
            b = ring[(i + 1) % TREE_SIDES]
            all_indices.extend([tip, b, a])

        # Base cap — fan from ring[0], CCW when viewed from below (normal = -Y)
        for i in range(1, TREE_SIDES - 1):
            all_indices.extend([ring[0], ring[i + 1], ring[i]])

    if not all_positions:
        _write_placeholder_glb(out_path)
        return

    pos_arr = np.array(all_positions, dtype=np.float32)
    idx_arr = np.array(all_indices,   dtype=np.uint32)

    pos_bytes = pos_arr.tobytes()
    idx_bytes = idx_arr.tobytes()

    pos_bv_len = len(pos_bytes)
    idx_bv_len = len(idx_bytes)
    pos_bv_aligned = _pad4(pos_bytes)
    idx_bv_aligned = _pad4(idx_bytes)
    bin_data = pos_bv_aligned + idx_bv_aligned

    pos_min = pos_arr.min(axis=0).tolist()
    pos_max = pos_arr.max(axis=0).tolist()

    gltf = {
        "asset": {"version": "2.0", "generator": "brelly-vegetation"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "vegetation"}],
        "meshes": [{
            "name": "vegetation",
            "primitives": [{
                "attributes": {"POSITION": 0},
                "indices": 1,
                "material": 0,
                "mode": 4,
            }],
        }],
        "materials": [{
            "name": "vegetation",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.15, 0.40, 0.12, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "doubleSided": True,
        }],
        "accessors": [
            {
                "bufferView": 0, "componentType": 5126, "count": len(all_positions),
                "type": "VEC3", "min": pos_min, "max": pos_max,
            },
            {
                "bufferView": 1, "componentType": 5125, "count": len(all_indices),
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0,            "byteLength": pos_bv_len, "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_bv_aligned), "byteLength": idx_bv_len, "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_data)}],
    }

    json_raw  = __import__("json").dumps(gltf, separators=(',', ':')).encode()
    json_pad  = b' ' * ((4 - len(json_raw) % 4) % 4)
    json_full = json_raw + json_pad

    bin_pad  = b'\x00' * ((4 - len(bin_data) % 4) % 4)
    bin_full = bin_data + bin_pad

    json_chunk = struct.pack('<II', len(json_full), 0x4E4F534A) + json_full
    bin_chunk  = struct.pack('<II', len(bin_full),  0x004E4942) + bin_full
    total = 12 + len(json_chunk) + len(bin_chunk)
    header = struct.pack('<III', 0x46546C67, 2, total)

    out_path.write_bytes(header + json_chunk + bin_chunk)


def _write_placeholder_glb(path: Path) -> None:
    json_content = b'{"asset":{"version":"2.0"}}'
    padding = (4 - len(json_content) % 4) % 4
    json_content += b' ' * padding
    chunk0 = struct.pack('<II', len(json_content), 0x4E4F534A) + json_content
    total = 12 + len(chunk0)
    header = struct.pack('<III', 0x46546C67, 2, total)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + chunk0)


# ── Pipeline entry ─────────────────────────────────────────────────────────────

def main(config_path: str) -> None:
    random.seed(RANDOM_SEED)
    config_dict = read_json(config_path)
    config = config_from_dict(config_dict)
    out_dir = output_dir(config_dict)
    gpkg_path = str(out_dir / "reprojected.gpkg")
    dem_ds = _open_dem(config_dict)

    positions = []

    try:
        from osgeo import ogr, gdal
        gdal.PushErrorHandler("CPLQuietErrorHandler")
        ds = ogr.Open(gpkg_path)
        if ds:
            # 1 — individually surveyed trees
            for layer_name in ["tlm_bb_einzelbaum", "tlm_bb_einzelbaum_gebuesch", "tlm_einzelbaum_gebuesch"]:
                lyr = ds.GetLayerByName(layer_name)
                if lyr is None:
                    continue
                total = lyr.GetFeatureCount()
                for j, feat in enumerate(lyr, 1):
                    geom = feat.GetGeometryRef()
                    if geom is None:
                        continue
                    pt = geom.GetGeometryRef(0) if geom.GetGeometryCount() > 0 else geom
                    if pt is None:
                        continue
                    e, n = pt.GetX(), pt.GetY()
                    raw_elev = pt.GetZ() if pt.Is3D() else config.base_elevation
                    elev = _sample_dem(dem_ds, e, n, raw_elev)
                    x, y, z = lv95_to_enu(e, n, elev, config)
                    if abs(x) > config.radius_m or abs(z) > config.radius_m:
                        continue
                    positions.append({"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)})
                    if total > 0 and (j % max(1, total // 20) == 0 or j == total):
                        progress("loading trees", j, total)
                break

            # 2 — scatter trees into forest polygons
            lyr = ds.GetLayerByName("tlm_bb_bodenbedeckung")
            if lyr:
                forest_polys = []
                for feat in lyr:
                    obj = feat.GetField(feat.GetFieldIndex("objektart"))
                    if obj in FOREST_TYPES:
                        geom = feat.GetGeometryRef()
                        if geom:
                            forest_polys.append((geom.Clone(), geom.GetArea()))

                total_area = sum(a for _, a in forest_polys)
                print(f"Forest polygons: {len(forest_polys)}, total area: {total_area/10000:.0f} ha")

                for geom, area in forest_polys:
                    area_ha = area / 10_000
                    budget_share = max(1, int(FOREST_TREE_BUDGET * area / total_area))
                    density_cap = max(1, int(area_ha * MAX_TREES_PER_HA))
                    quota = min(budget_share, density_cap)
                    lv95_pts = _scatter_in_polygon(geom, quota, config.base_elevation)
                    for e, n, _ in lv95_pts:
                        x, y, z = lv95_to_enu(e, n, config.base_elevation, config)
                        if abs(x) > config.radius_m or abs(z) > config.radius_m:
                            continue
                        elev = _sample_dem(dem_ds, e, n, config.base_elevation)
                        _, y, _ = lv95_to_enu(e, n, elev, config)
                        positions.append({"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)})

        gdal.PopErrorHandler()
    except (ImportError, Exception) as exc:
        print(f"WARNING: Could not extract vegetation ({exc}). Writing empty list.")

    # Write vegetation.json (used by road-graph and other consumers)
    out_path = out_dir / "vegetation.json"
    write_json(str(out_path), {"positions": positions})
    print(f"Vegetation: {len(positions)} trees → {out_path}")

    # Write vegetation.glb directly — no Blender needed
    out_glb = out_dir / "vegetation.glb"
    write_vegetation_glb(positions, out_glb)
    print(f"Vegetation GLB → {out_glb}  ({len(positions)} trees)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
