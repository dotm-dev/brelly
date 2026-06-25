#!/usr/bin/env python3
"""
Extract centre coordinates and base elevation from an alti3D VRT.
Run from the Brelly project root with the venv active:
    python pipeline/inspect_area.py data/<area>/alti3d.vrt
"""
import sys
from osgeo import gdal

gdal.UseExceptions()

if len(sys.argv) < 2:
    print("Usage: python pipeline/inspect_area.py data/<area>/alti3d.vrt", file=sys.stderr)
    sys.exit(1)

ds = gdal.Open(sys.argv[1])
if ds is None:
    print(f"Cannot open {sys.argv[1]}", file=sys.stderr)
    sys.exit(1)

gt   = ds.GetGeoTransform()
cols = ds.RasterXSize
rows = ds.RasterYSize

cx = gt[0] + (cols / 2) * gt[1]
cy = gt[3] + (rows / 2) * gt[5]

band   = ds.GetRasterBand(1)
nodata = band.GetNoDataValue()
px, py = int(cols / 2), int(rows / 2)
arr    = band.ReadAsArray(max(0, px - 1), max(0, py - 1), 3, 3)
valid  = arr[arr != nodata].flatten() if nodata is not None else arr.flatten()
elev   = float(valid.mean()) if len(valid) > 0 else 0.0

print(f"CENTER_E={cx:.0f}")
print(f"CENTER_N={cy:.0f}")
print(f"BASE_ELEVATION={elev:.1f}")
