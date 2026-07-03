# pipeline/tests/test_download_step.py
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest

gdal = pytest.importorskip("osgeo.gdal")

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib
download_step = importlib.import_module("00_download")


def _make_tif(path: Path, ox: float, oy: float, size: int = 10, px: float = 1.0, value: float = 450.0) -> None:
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((ox, px, 0, oy, 0, -px))
    band = ds.GetRasterBand(1)
    band.WriteArray(np.full((size, size), value, dtype=np.float32))
    band.SetNoDataValue(-9999.0)
    ds.FlushCache()
    ds = None


def test_rebuild_vrt_returns_true_on_success(tmp_path):
    _make_tif(tmp_path / "a.tif", ox=2683000.0, oy=1247510.0)
    vrt_path = tmp_path / "alti3d.vrt"
    assert download_step._rebuild_vrt(vrt_path, tmp_path) is True
    assert vrt_path.exists()


def test_rebuild_vrt_returns_false_when_no_tifs(tmp_path):
    vrt_path = tmp_path / "alti3d.vrt"
    assert download_step._rebuild_vrt(vrt_path, tmp_path) is False
    assert not vrt_path.exists()


def test_refresh_derived_fields_rewrites_when_base_elevation_is_placeholder(tmp_path):
    _make_tif(tmp_path / "a.tif", ox=2683000.0, oy=1247510.0, value=612.3)
    vrt_path = tmp_path / "alti3d.vrt"
    download_step._rebuild_vrt(vrt_path, tmp_path)

    config_path = tmp_path / "my_map.json"
    config = {
        "name": "my_map", "center_e": 0.0, "center_n": 0.0,
        "radius_m": 1000.0, "base_elevation": 0.0,
        "source_data": {"dem": str(vrt_path), "tlm": "data/tlm.gpkg"},
    }
    config_path.write_text(json.dumps(config))

    download_step._refresh_derived_fields(str(config_path), config, vrt_path)

    written = json.loads(config_path.read_text())
    assert written["base_elevation"] == pytest.approx(612.3)
    assert written["center_e"] == pytest.approx(2683005.0)
    assert written["source_data"]["tlm"] == "data/tlm.gpkg"


def test_refresh_derived_fields_leaves_nonzero_base_elevation_alone(tmp_path):
    config_path = tmp_path / "my_map.json"
    config = {
        "name": "my_map", "center_e": 111.0, "center_n": 222.0,
        "radius_m": 500.0, "base_elevation": 916.1,
        "source_data": {"dem": "data/my_map/alti3d.vrt", "tlm": "data/tlm.gpkg"},
    }
    config_path.write_text(json.dumps(config))
    original_text = config_path.read_text()

    download_step._refresh_derived_fields(str(config_path), config, Path("data/my_map/alti3d.vrt"))

    assert config_path.read_text() == original_text
