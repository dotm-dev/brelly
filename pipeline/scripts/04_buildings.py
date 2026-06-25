#!/usr/bin/env python3
# pipeline/scripts/04_buildings.py
"""Generate buildings.glb from TLM building footprints via Blender."""
import sys, json, subprocess, shutil, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.io import read_json, ensure_dir, output_dir, progress
from utils.coords import config_from_dict, lv95_to_enu


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

    blender = shutil.which("blender")
    if not blender:
        print("WARNING: Blender not found. Writing placeholder buildings.glb.")
        write_placeholder_glb(out_glb)
        return

    buildings_data = _load_buildings(out_dir / "reprojected.gpkg", config)
    if not buildings_data:
        print("WARNING: No building data found. Writing placeholder buildings.glb.")
        write_placeholder_glb(out_glb)
        return
    buildings_json = out_dir / "_buildings_data.json"
    buildings_json.write_text(json.dumps(buildings_data))
    baker = Path(__file__).parent.parent / "blender" / "building_baker.py"
    print(f"Baking {len(buildings_data)} buildings in Blender…", flush=True)
    try:
        result = subprocess.run(
            [blender, "--background", "--factory-startup", "--python", str(baker),
             "--", str(buildings_json), str(out_glb)],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("WARNING: Blender timed out after 300s. Writing placeholder buildings.glb.")
        buildings_json.unlink(missing_ok=True)
        write_placeholder_glb(out_glb)
        return
    buildings_json.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"WARNING: Blender building bake failed.\n{result.stderr[-500:]}")
        write_placeholder_glb(out_glb)
    else:
        print(f"Buildings GLB → {out_glb}")


def _extract_polygons(geom) -> list:
    """Return a flat list of Polygon geometries from a Polygon or MultiPolygon."""
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
            # accept Polygon / Polygon25D / MultiPolygon / MultiPolygon25D
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
