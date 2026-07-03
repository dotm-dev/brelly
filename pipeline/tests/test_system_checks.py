# pipeline/tests/test_system_checks.py
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch
import pytest

from system_checks import CheckResult, run_all_checks, check_command, map_data_ready


def test_check_command_found():
    with patch("shutil.which", return_value="/usr/bin/blender"):
        result = check_command("blender", "Blender")
        assert result.ok is True
        assert result.name == "Blender"


def test_check_command_missing():
    with patch("shutil.which", return_value=None):
        result = check_command("blender", "Blender")
        assert result.ok is False


def test_run_all_checks_returns_named_results(tmp_path):
    results = run_all_checks(project_root=tmp_path)
    names = [r.name for r in results]
    assert "Python 3.12" in names
    assert "GDAL system library" in names
    assert "Virtual environment" in names
    assert "Python dependencies" in names
    assert "Blender" in names
    assert "gltfpack" in names


def test_map_data_ready_true_when_both_sources_exist(tmp_path):
    dem = tmp_path / "data" / "my_map" / "alti3d.vrt"
    dem.parent.mkdir(parents=True)
    dem.write_text("<VRTDataset></VRTDataset>")
    tlm = tmp_path / "shared" / "swissTLM3D.gpkg"
    tlm.parent.mkdir(parents=True)
    tlm.write_text("fake gpkg content")

    config_path = tmp_path / "my_map.json"
    config_path.write_text(json.dumps({
        "name": "my_map",
        "source_data": {"dem": str(dem.relative_to(tmp_path)), "tlm": str(tlm.relative_to(tmp_path))},
    }))

    result = map_data_ready(config_path, project_root=tmp_path)
    assert result.ok is True
    assert result.name == "my_map"


def test_map_data_ready_false_and_names_missing_sources(tmp_path):
    config_path = tmp_path / "my_map.json"
    config_path.write_text(json.dumps({"name": "my_map", "source_data": {}}))

    result = map_data_ready(config_path, project_root=tmp_path)
    assert result.ok is False
    assert "DEM" in result.detail
    assert "TLM" in result.detail


def test_map_data_ready_false_for_invalid_config_file(tmp_path):
    config_path = tmp_path / "broken.json"
    config_path.write_text("not valid json")

    result = map_data_ready(config_path, project_root=tmp_path)
    assert result.ok is False


def test_map_data_ready_true_pending_when_dem_missing_but_csv_staged(tmp_path):
    """New Map's swisstopo-CSV mode creates a config before any tile is
    downloaded — the DEM VRT doesn't exist yet on purpose. That should
    read as ready-but-pending, not broken, since 00_download.py fetches
    it automatically on the next pipeline run."""
    dem_dir = tmp_path / "data" / "my_map"
    dem_dir.mkdir(parents=True)
    (dem_dir / "ch.swisstopo.swissalti3d-abc123.csv").write_text("https://example.com/tile.tif\n")
    tlm = tmp_path / "shared" / "swissTLM3D.gpkg"
    tlm.parent.mkdir(parents=True)
    tlm.write_text("fake gpkg content")

    config_path = tmp_path / "my_map.json"
    config_path.write_text(json.dumps({
        "name": "my_map",
        "source_data": {
            "dem": str((dem_dir / "alti3d.vrt").relative_to(tmp_path)),
            "tlm": str(tlm.relative_to(tmp_path)),
        },
    }))

    result = map_data_ready(config_path, project_root=tmp_path)
    assert result.ok is True
    assert "download" in result.detail.lower()


def test_map_data_ready_false_when_dem_missing_and_no_csv_staged(tmp_path):
    dem_dir = tmp_path / "data" / "my_map"
    dem_dir.mkdir(parents=True)
    tlm = tmp_path / "shared" / "swissTLM3D.gpkg"
    tlm.parent.mkdir(parents=True)
    tlm.write_text("fake gpkg content")

    config_path = tmp_path / "my_map.json"
    config_path.write_text(json.dumps({
        "name": "my_map",
        "source_data": {
            "dem": str((dem_dir / "alti3d.vrt").relative_to(tmp_path)),
            "tlm": str(tlm.relative_to(tmp_path)),
        },
    }))

    result = map_data_ready(config_path, project_root=tmp_path)
    assert result.ok is False
    assert "DEM" in result.detail


def test_run_single_check_blender_matches_check_blender():
    from system_checks import run_single_check, check_blender
    result = run_single_check("Blender", project_root=Path("."))
    expected = check_blender()
    assert result.name == expected.name
    assert result.ok == expected.ok


def test_run_single_check_unknown_name_raises_keyerror():
    from system_checks import run_single_check
    with pytest.raises(KeyError):
        run_single_check("Nonexistent Check", project_root=Path("."))
