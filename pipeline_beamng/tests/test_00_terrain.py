import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

gdal = pytest.importorskip("osgeo.gdal")
numpy = pytest.importorskip("numpy")

spec = importlib.util.spec_from_file_location(
    "beamng_terrain_step", Path(__file__).parent.parent / "scripts" / "00_terrain.py"
)
terrain_step = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terrain_step)


def _make_dem(path: Path, center_e: float, center_n: float, radius_m: float) -> None:
    """A flat 20x20 DEM tile covering the map area at elevation 460m, wrapped in a VRT
    (matching how source_data.dem is used elsewhere: a .vrt mosaic path)."""
    size = 20
    px = (radius_m * 2.2) / size
    ox = center_e - radius_m * 1.1
    oy = center_n + radius_m * 1.1
    tif_path = path.parent / "tile.tif"
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(tif_path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((ox, px, 0, oy, 0, -px))
    band = ds.GetRasterBand(1)
    band.WriteArray(numpy.full((size, size), 460.0, dtype=numpy.float32))
    band.SetNoDataValue(-9999.0)
    ds.FlushCache()
    ds = None

    vrt_opts = gdal.BuildVRTOptions(resampleAlg="nearest")
    vds = gdal.BuildVRT(str(path), [str(tif_path)], options=vrt_opts)
    vds.FlushCache()


def test_choose_grid_size_picks_power_of_two_bracket():
    # target = diameter / 2m-per-pixel: radius 250 -> 250px -> 512;
    # radius 600 -> 600px -> 1024; radius 1200 -> 1200px -> 2048
    assert terrain_step._choose_grid_size(250) == 512
    assert terrain_step._choose_grid_size(600) == 1024
    assert terrain_step._choose_grid_size(1200) == 2048


def test_main_writes_terrain_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dem_dir = tmp_path / "data" / "test_area"
    dem_dir.mkdir(parents=True)
    dem_path = dem_dir / "alti3d.vrt"
    _make_dem(dem_path, center_e=2683000.0, center_n=1247500.0, radius_m=100.0)

    config = {
        "name": "test_area",
        "center_e": 2683000.0,
        "center_n": 1247500.0,
        "radius_m": 100.0,
        "base_elevation": 450.0,
        "source_data": {"dem": str(dem_path)},
    }
    config_path = tmp_path / "test_area.json"
    config_path.write_text(json.dumps(config))

    terrain_step.main(str(config_path))

    out_dir = tmp_path / "maps" / "test_area" / "beamng" / "test_area"
    assert (out_dir / "test_area.ter").exists()
    assert (out_dir / "test_area.terrain.json").exists()
    assert (out_dir / "test_area_heightmap.png").exists()

    objs_path = tmp_path / "maps" / "test_area" / "beamng" / "test_area" / "_terrain_objects.json"
    objs = json.loads(objs_path.read_text())
    assert len(objs) == 1
    assert objs[0]["class"] == "TerrainBlock"
