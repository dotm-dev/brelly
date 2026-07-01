# pipeline/dem_config.py
"""Pure functions deriving map config fields (center, radius, base
elevation) from a DEM VRT/GeoTIFF, so the New Map GUI screen can build a
config without the user typing coordinates by hand."""
from __future__ import annotations


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
