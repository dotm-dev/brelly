# pipeline/dem_config.py
"""Pure functions deriving map config fields (center, radius, base
elevation) from a DEM VRT/GeoTIFF, so the New Map GUI screen can build a
config without the user typing coordinates by hand."""
from __future__ import annotations

import re
from pathlib import Path

# swissALTI3D tile filenames encode their SW corner on a fixed 1km LV95
# grid, e.g. swissalti3d_2022_2713-1089_0.5_2056_5728.tif -> easting
# 2713000, northing 1089000. This lets us compute an exact extent from a
# swisstopo download-URL CSV alone, before any tile is actually downloaded.
_TILE_GRID_RE = re.compile(r"_(\d{4})-(\d{4})_")


def dem_extent(dem_path: str) -> tuple[float, float, float, float]:
    """Return (min_e, max_e, min_n, max_n) for the DEM's raster extent, in
    the DEM's native CRS units (LV95 metres for swissALTI3D)."""
    from osgeo import gdal
    ds = gdal.Open(dem_path)
    if ds is None:
        raise ValueError(f"Cannot open DEM: {dem_path}")
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    min_e, max_e = gt[0], gt[0] + w * gt[1]
    max_n, min_n = gt[3], gt[3] + h * gt[5]
    return min_e, max_e, min_n, max_n


def dem_center(dem_path: str) -> tuple[float, float]:
    """Return (center_e, center_n) — the midpoint of the DEM's raster extent."""
    min_e, max_e, min_n, max_n = dem_extent(dem_path)
    return (min_e + max_e) / 2.0, (min_n + max_n) / 2.0


def sample_elevation(dem_path: str, e: float, n: float) -> float:
    """Sample the DEM's elevation value at LV95 coordinate (e, n)."""
    from osgeo import gdal
    ds = gdal.Open(dem_path)
    if ds is None:
        raise ValueError(f"Cannot open DEM: {dem_path}")
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    col = int((e - gt[0]) / gt[1])
    row = int((n - gt[3]) / gt[5])
    col = max(0, min(col, w - 1))
    row = max(0, min(row, h - 1))
    band = ds.GetRasterBand(1)
    value = band.ReadAsArray(col, row, 1, 1)[0][0]
    return float(value)


def derive_config_fields(dem_path: str) -> dict:
    """Derive center_e, center_n, radius_m, base_elevation from a DEM VRT."""
    from utils.coords import radius_from_dem

    center_e, center_n = dem_center(dem_path)
    radius_m = radius_from_dem(dem_path, center_e, center_n) or 500.0
    base_elevation = sample_elevation(dem_path, center_e, center_n)
    return {
        "center_e": center_e,
        "center_n": center_n,
        "radius_m": radius_m,
        "base_elevation": round(base_elevation, 2),
    }


def extent_from_swisstopo_csv(csv_path: str) -> tuple[float, float, float, float]:
    """Return (min_e, max_e, min_n, max_n) in LV95 metres, parsed from the
    tile filenames listed in a swisstopo download-URL CSV — no download
    needed, since tiles snap to a fixed 1km grid encoded in their names."""
    lines = [line.strip() for line in Path(csv_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"No URLs found in {csv_path}")

    eastings_km: list[int] = []
    northings_km: list[int] = []
    for line in lines:
        match = _TILE_GRID_RE.search(Path(line).name)
        if match:
            eastings_km.append(int(match.group(1)))
            northings_km.append(int(match.group(2)))

    if not eastings_km:
        raise ValueError(f"Could not parse tile grid coordinates from any line in {csv_path}")

    min_e, max_e = min(eastings_km) * 1000.0, (max(eastings_km) + 1) * 1000.0
    min_n, max_n = min(northings_km) * 1000.0, (max(northings_km) + 1) * 1000.0
    return min_e, max_e, min_n, max_n


def derive_config_fields_from_csv(csv_path: str) -> dict:
    """Same shape as derive_config_fields(), but from a swisstopo CSV before
    any tile is downloaded. center_e/center_n/radius_m are exact (the tile
    grid is exact); base_elevation is left at 0.0 since elevation can only
    come from real raster data — 00_download.py recomputes and overwrites
    all four fields once the tiles are actually downloaded."""
    min_e, max_e, min_n, max_n = extent_from_swisstopo_csv(csv_path)
    return {
        "center_e": (min_e + max_e) / 2.0,
        "center_n": (min_n + max_n) / 2.0,
        "radius_m": max(max_e - min_e, max_n - min_n) / 2.0,
        "base_elevation": 0.0,
    }
