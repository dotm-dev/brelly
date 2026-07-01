# pipeline/utils/dem.py
"""Shared DEM/VRT helpers used by the download step and the New Map GUI screen."""
from pathlib import Path


def build_vrt(tif_paths: list[str], vrt_path: Path) -> bool:
    """Build a VRT mosaic from a list of GeoTIFF paths. Returns False if the
    list is empty or GDAL is unavailable; True on success."""
    if not tif_paths:
        return False
    try:
        from osgeo import gdal
        gdal.UseExceptions()
    except ImportError:
        return False

    vrt_opts = gdal.BuildVRTOptions(resampleAlg="nearest")
    ds = gdal.BuildVRT(str(vrt_path), tif_paths, options=vrt_opts)
    if ds is None:
        return False
    ds.FlushCache()
    ds = None
    return True
