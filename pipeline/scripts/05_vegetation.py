#!/usr/bin/env python3
# pipeline/scripts/05_vegetation.py
"""Extract tree positions from TLM, write vegetation.json, bake vegetation.glb via Blender."""
import math, random, sys, shutil, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.io import read_json, write_json, output_dir, progress
from utils.coords import config_from_dict, lv95_to_enu, bbox_from_center

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
    # Grid spacing that would give roughly n_trees points (with ~60% hit rate)
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
                    elev = pt.GetZ() if pt.Is3D() else config.base_elevation
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

    out_path = out_dir / "vegetation.json"
    write_json(str(out_path), {"positions": positions})
    print(f"Vegetation: {len(positions)} trees → {out_path}")

    blender = shutil.which("blender")
    if not blender:
        print("WARNING: Blender not found. Skipping vegetation.glb bake.")
        return
    out_glb = out_dir / "vegetation.glb"
    baker = Path(__file__).parent.parent / "blender" / "vegetation_baker.py"
    print(f"Baking {len(positions)} trees in Blender…", flush=True)
    try:
        result = subprocess.run(
            [blender, "--background", "--factory-startup", "--python", str(baker),
             "--", str(out_path), str(out_glb)],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("WARNING: Blender timed out after 600s. Skipping vegetation.glb.")
        return
    if result.returncode != 0:
        print(f"WARNING: Blender vegetation bake failed.\n{result.stderr[-500:]}")
    else:
        print(f"Vegetation GLB → {out_glb}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
