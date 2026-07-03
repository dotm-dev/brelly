# pipeline/tests/test_new_map_screen.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from screens.new_map import is_valid_map_name, build_new_map_config


def test_is_valid_map_name_accepts_alnum_dash_underscore():
    assert is_valid_map_name("bre") is True
    assert is_valid_map_name("test-area_1") is True


def test_is_valid_map_name_rejects_empty():
    assert is_valid_map_name("") is False


def test_is_valid_map_name_rejects_spaces_and_slashes():
    assert is_valid_map_name("my map") is False
    assert is_valid_map_name("../etc") is False


def test_build_new_map_config_matches_expected_schema():
    fields = {
        "center_e": 2683005.0, "center_n": 1247505.0,
        "radius_m": 500.0, "base_elevation": 612.3,
    }
    config = build_new_map_config("bre", "Bre", "/data/tlm.gpkg", fields)

    assert config["name"] == "bre"
    assert config["displayName"] == "Bre"
    assert config["center_e"] == 2683005.0
    assert config["base_elevation"] == 612.3
    assert config["source_data"]["tlm"] == "/data/tlm.gpkg"
    assert config["source_data"]["dem"] == str(Path("data") / "bre" / "alti3d.vrt")
    assert config["checkpoints"] == []
