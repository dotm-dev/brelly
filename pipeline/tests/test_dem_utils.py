# pipeline/tests/test_dem_utils.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

gdal = pytest.importorskip("osgeo.gdal")
numpy = pytest.importorskip("numpy")

from utils.dem import build_vrt


def _make_tif(path: Path, ox: float, oy: float, size: int = 4, px: float = 1.0) -> None:
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((ox, px, 0, oy, 0, -px))
    band = ds.GetRasterBand(1)
    band.WriteArray(numpy.array([[10.0] * size for _ in range(size)]))
    band.SetNoDataValue(-9999.0)
    ds.FlushCache()
    ds = None


def test_build_vrt_creates_file_from_tiles(tmp_path):
    tif1 = tmp_path / "a.tif"
    tif2 = tmp_path / "b.tif"
    _make_tif(tif1, ox=2683000, oy=1247500)
    _make_tif(tif2, ox=2683004, oy=1247500)
    vrt_path = tmp_path / "mosaic.vrt"

    build_vrt([str(tif1), str(tif2)], vrt_path)

    assert vrt_path.exists()
    ds = gdal.Open(str(vrt_path))
    assert ds is not None
    assert ds.RasterXSize == 8


def test_build_vrt_empty_tile_list_returns_false(tmp_path):
    vrt_path = tmp_path / "mosaic.vrt"
    result = build_vrt([], vrt_path)
    assert result is False
    assert not vrt_path.exists()
