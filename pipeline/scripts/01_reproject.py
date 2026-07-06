#!/usr/bin/env python3
# pipeline/scripts/01_reproject.py
"""Clip source data to bounding box and write a reprojected working GeoPackage.

Input:  config source_data.tlm  (SwissTLM3D .gpkg, LV95)
Output: maps/<name>/reprojected.gpkg  (same CRS, clipped to bbox)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.io import read_json, ensure_dir, output_dir
from shared.utils.coords import config_from_dict, bbox_from_center


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    config = config_from_dict(config_dict)
    bbox = bbox_from_center(config)
    out_dir = ensure_dir(output_dir(config_dict))
    tlm_path = config_dict["source_data"]["tlm"]

    try:
        from osgeo import gdal
        gdal.UseExceptions()
    except ImportError:
        print("WARNING: GDAL not available. Skipping reproject — pipeline will use empty data.")
        _write_empty_gpkg(out_dir / "reprojected.gpkg")
        return

    if not Path(tlm_path).exists():
        print(f"WARNING: TLM source not found at {tlm_path}. Writing empty GeoPackage.")
        _write_empty_gpkg(out_dir / "reprojected.gpkg")
        return

    out_path = str(out_dir / "reprojected.gpkg")
    if Path(out_path).exists():
        Path(out_path).unlink()

    clip_wkt = (
        f"POLYGON(({bbox['min_e']} {bbox['min_n']},"
        f"{bbox['max_e']} {bbox['min_n']},"
        f"{bbox['max_e']} {bbox['max_n']},"
        f"{bbox['min_e']} {bbox['max_n']},"
        f"{bbox['min_e']} {bbox['min_n']}))"
    )

    print(f"  Clipping {Path(tlm_path).name} to bbox "
          f"({(bbox['max_e']-bbox['min_e'])/1000:.1f} km × "
          f"{(bbox['max_n']-bbox['min_n'])/1000:.1f} km)…", flush=True)

    gdal.PushErrorHandler("CPLQuietErrorHandler")
    gdal.VectorTranslate(
        out_path,
        tlm_path,
        format="GPKG",
        spatFilter=(bbox['min_e'], bbox['min_n'], bbox['max_e'], bbox['max_n']),
    )
    gdal.PopErrorHandler()

    print(f"Reprojected data clipped to bbox → {out_path}")


def _write_empty_gpkg(path: Path) -> None:
    try:
        from osgeo import ogr
        driver = ogr.GetDriverByName("GPKG")
        if Path(path).exists():
            driver.DeleteDataSource(str(path))
        driver.CreateDataSource(str(path))
        print(f"Empty GeoPackage written → {path}")
    except ImportError:
        path.touch()
        print(f"Placeholder file written → {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
