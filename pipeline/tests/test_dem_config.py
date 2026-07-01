# pipeline/tests/test_dem_config.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest

gdal = pytest.importorskip("osgeo.gdal")

from dem_config import dem_extent, dem_center, sample_elevation, derive_config_fields


def _make_tif(path: Path, ox: float, oy: float, size: int = 10, px: float = 1.0, value: float = 450.0) -> None:
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((ox, px, 0, oy, 0, -px))
    band = ds.GetRasterBand(1)
    band.WriteArray(np.full((size, size), value, dtype=np.float32))
    band.SetNoDataValue(-9999.0)
    ds.FlushCache()
    ds = None


def test_dem_extent(tmp_path):
    tif = tmp_path / "dem.tif"
    _make_tif(tif, ox=2683000.0, oy=1247510.0, size=10, px=1.0)
    min_e, max_e, min_n, max_n = dem_extent(str(tif))
    assert min_e == pytest.approx(2683000.0)
    assert max_e == pytest.approx(2683010.0)
    assert min_n == pytest.approx(1247500.0)
    assert max_n == pytest.approx(1247510.0)


def test_dem_center(tmp_path):
    tif = tmp_path / "dem.tif"
    _make_tif(tif, ox=2683000.0, oy=1247510.0, size=10, px=1.0)
    center_e, center_n = dem_center(str(tif))
    assert center_e == pytest.approx(2683005.0)
    assert center_n == pytest.approx(1247505.0)


def test_sample_elevation(tmp_path):
    tif = tmp_path / "dem.tif"
    _make_tif(tif, ox=2683000.0, oy=1247510.0, size=10, px=1.0, value=612.3)
    elev = sample_elevation(str(tif), 2683005.0, 1247505.0)
    assert elev == pytest.approx(612.3)


def test_derive_config_fields(tmp_path):
    tif = tmp_path / "dem.tif"
    _make_tif(tif, ox=2683000.0, oy=1247510.0, size=10, px=1.0, value=612.3)
    fields = derive_config_fields(str(tif))
    assert fields["center_e"] == pytest.approx(2683005.0)
    assert fields["center_n"] == pytest.approx(1247505.0)
    assert fields["base_elevation"] == pytest.approx(612.3)
    assert fields["radius_m"] > 0


def test_dem_extent_raises_on_invalid_path(tmp_path):
    with pytest.raises(ValueError):
        dem_extent(str(tmp_path / "does_not_exist.tif"))
