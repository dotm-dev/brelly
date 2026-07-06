# pipeline/tests/test_coords.py
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.coords import lv95_to_enu, enu_to_lv95, bbox_from_center, Config


def test_lv95_to_enu_origin_is_zero():
    config = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0)
    x, y, z = lv95_to_enu(2683000.0, 1247500.0, 450.0, config)
    assert abs(x) < 1e-6
    assert abs(y) < 1e-6
    assert abs(z) < 1e-6


def test_lv95_to_enu_east_offset():
    config = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0)
    x, y, z = lv95_to_enu(2683100.0, 1247500.0, 450.0, config)
    assert abs(x - 100.0) < 1e-3
    assert abs(z) < 1e-3


def test_lv95_to_enu_north_offset():
    config = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0)
    x, y, z = lv95_to_enu(2683000.0, 1247600.0, 450.0, config)
    assert abs(z - 100.0) < 1e-3
    assert abs(x) < 1e-3


def test_lv95_to_enu_elevation_offset():
    config = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0)
    x, y, z = lv95_to_enu(2683000.0, 1247500.0, 460.0, config)
    assert abs(y - 10.0) < 1e-3


def test_enu_to_lv95_roundtrip():
    config = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0)
    e_orig, n_orig, elev_orig = 2683123.0, 1247678.0, 512.5
    x, y, z = lv95_to_enu(e_orig, n_orig, elev_orig, config)
    e_back, n_back, elev_back = enu_to_lv95(x, y, z, config)
    assert abs(e_back - e_orig) < 1e-3
    assert abs(n_back - n_orig) < 1e-3
    assert abs(elev_back - elev_orig) < 1e-3


def test_bbox_from_center():
    config = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0, radius_m=500.0)
    bbox = bbox_from_center(config)
    assert bbox["min_e"] == pytest.approx(2682500.0)
    assert bbox["max_e"] == pytest.approx(2683500.0)
    assert bbox["min_n"] == pytest.approx(1247000.0)
    assert bbox["max_n"] == pytest.approx(1248000.0)
