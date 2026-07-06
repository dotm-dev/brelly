# pipeline/utils/coords.py
"""LV95 (EPSG:2056) ↔ local ENU coordinate utilities.

Local ENU origin = (center_e, center_n, base_elevation) in LV95.
  X = metres east of origin
  Y = metres above base_elevation
  Z = metres north of origin
"""
from dataclasses import dataclass, field


@dataclass
class Config:
    """Subset of map config used by coordinate utilities."""
    center_e: float
    center_n: float
    base_elevation: float
    radius_m: float = 500.0


def lv95_to_enu(e: float, n: float, elevation: float, config: Config) -> tuple[float, float, float]:
    """Convert LV95 coordinates to local ENU (metres from origin)."""
    x = e - config.center_e
    y = elevation - config.base_elevation
    z = n - config.center_n
    return x, y, z


def enu_to_lv95(x: float, y: float, z: float, config: Config) -> tuple[float, float, float]:
    """Convert local ENU back to LV95 coordinates."""
    e = x + config.center_e
    elevation = y + config.base_elevation
    n = z + config.center_n
    return e, n, elevation


def bbox_from_center(config: Config) -> dict:
    """Return LV95 axis-aligned bounding box for the map area."""
    return {
        "min_e": config.center_e - config.radius_m,
        "max_e": config.center_e + config.radius_m,
        "min_n": config.center_n - config.radius_m,
        "max_n": config.center_n + config.radius_m,
    }


def radius_from_dem(dem_path: str, center_e: float, center_n: float) -> float | None:
    """Return the largest square radius centred at (center_e, center_n) that fits inside the DEM."""
    try:
        from osgeo import gdal
        ds = gdal.Open(dem_path)
        if ds is None:
            return None
        gt = ds.GetGeoTransform()
        w, h = ds.RasterXSize, ds.RasterYSize
        min_e, max_e = gt[0], gt[0] + w * gt[1]
        max_n, min_n = gt[3], gt[3] + h * gt[5]
        r = min(center_e - min_e, max_e - center_e,
                center_n - min_n, max_n - center_n)
        return max(r, 0.0) if r > 0 else None
    except Exception:
        return None


def config_from_dict(d: dict) -> Config:
    """Build a Config from a map config dict. Auto-detects radius from DEM when not set."""
    center_e = float(d["center_e"])
    center_n = float(d["center_n"])

    if "radius_m" in d:
        radius_m = float(d["radius_m"])
    else:
        dem_path = d.get("source_data", {}).get("dem", "")
        detected = radius_from_dem(dem_path, center_e, center_n) if dem_path else None
        import os
        if detected:
            if not os.environ.get("PIPELINE_QUIET"):
                print(f"  Auto-detected radius from DEM: {detected:.0f} m", flush=True)
            radius_m = detected
        else:
            radius_m = 500.0
            print(f"  WARNING: radius_m not set and DEM unreadable — defaulting to {radius_m:.0f} m")

    return Config(
        center_e=center_e,
        center_n=center_n,
        base_elevation=float(d["base_elevation"]),
        radius_m=radius_m,
    )
