#!/usr/bin/env python3
# pipeline_beamng/scripts/00_terrain.py
"""Generate BeamNG terrain files (.ter, .terrain.json, heightmap PNG) directly
from the map's DEM. Independent of pipeline/scripts/02_terrain.py's terrain.glb
output — that step never caches a raw heightmap grid (only the final glTF
mesh), so re-reading the DEM here is simpler and more robust than parsing a
glTF mesh back into a grid."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))                       # pipeline_beamng/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))                # repo root, for shared/

from shared.utils.io import read_json
from shared.utils.coords import config_from_dict, bbox_from_center

from formats.terrain import (
    encode_heightmap, write_ter_file, write_terrain_json,
    write_heightmap_png, terrainblock_object,
)


def _choose_grid_size(radius_m: float) -> int:
    """Pick a terrain grid size targeting ~2m/pixel, snapped up to the next
    power-of-two bracket BeamNG terrains commonly use."""
    target = (radius_m * 2) / 2.0
    for size in (512, 1024, 2048, 4096):
        if size >= target:
            return size
    return 4096


def _read_dem_grid(config_dict: dict, size: int):
    """Warp the DEM to a size x size grid, relative to base_elevation.

    Assumption (unverified in-game): row 0 of the returned grid is the
    NORTH edge of the map (standard GDAL raster convention — row 0 = top =
    max northing). If the terrain appears mirrored north/south once loaded
    in BeamNG, flip this with np.flipud(arr) here.
    """
    from osgeo import gdal
    import numpy as np
    gdal.UseExceptions()

    config = config_from_dict(config_dict)
    bbox = bbox_from_center(config)
    dem_path = config_dict["source_data"]["dem"]

    NODATA = -9999.0
    ds = gdal.Open(dem_path)
    mem_ds = gdal.Warp(
        "", ds, format="MEM",
        outputBounds=(bbox["min_e"], bbox["min_n"], bbox["max_e"], bbox["max_n"]),
        width=size, height=size, resampleAlg="bilinear", dstNodata=NODATA,
    )
    band = mem_ds.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    gdal.FillNodata(band, None, maxSearchDist=200, smoothingIterations=2)

    arr = band.ReadAsArray().astype(float)
    arr[arr == NODATA] = config.base_elevation
    arr -= config.base_elevation
    return arr


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    name = config_dict["name"]
    config = config_from_dict(config_dict)

    out_dir = Path("maps") / name / "beamng" / name
    out_dir.mkdir(parents=True, exist_ok=True)

    size = _choose_grid_size(config.radius_m)
    grid = _read_dem_grid(config_dict, size)

    heightmap_u16, position_z, max_height = encode_heightmap(grid.tolist())
    square_size = (config.radius_m * 2) / size
    materials = ["grass"]

    ter_path = out_dir / f"{name}.ter"
    png_path = out_dir / f"{name}_heightmap.png"
    json_path = out_dir / f"{name}.terrain.json"

    # Paths inside level files use the game-VFS form real maps use (terrain
    # files sit at the level root, e.g. "/levels/example/theTerrain.ter"),
    # not filesystem-relative paths.
    vfs_prefix = f"/levels/{name}"

    write_ter_file(ter_path, heightmap_u16, materials=materials)
    write_heightmap_png(png_path, heightmap_u16)
    write_terrain_json(
        json_path, size,
        ter_rel_path=f"{vfs_prefix}/{name}.ter",
        heightmap_png_rel_path=f"{vfs_prefix}/{name}_heightmap.png",
        materials=materials,
    )

    terrain_obj = terrainblock_object(
        name=f"{name}_terrain",
        position_xyz=(-config.radius_m, -config.radius_m, position_z),
        square_size=square_size,
        max_height=max_height,
        terrain_file_rel=f"{vfs_prefix}/{name}.ter",
    )
    (out_dir / "_terrain_objects.json").write_text(json.dumps([terrain_obj]))
    print(f"BeamNG terrain -> {ter_path} ({size}x{size}, maxHeight={max_height:.1f}m)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
