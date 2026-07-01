# pipeline/tests/test_system_checks.py
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

from system_checks import CheckResult, run_all_checks, check_command


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
    assert "DEM data" in names
    assert "TLM data" in names
    assert "Map config" in names


def test_run_all_checks_data_missing_when_no_data_dir(tmp_path):
    results = run_all_checks(project_root=tmp_path)
    dem_check = next(r for r in results if r.name == "DEM data")
    assert dem_check.ok is False


def test_run_all_checks_data_found(tmp_path):
    dem_dir = tmp_path / "data" / "my_area"
    dem_dir.mkdir(parents=True)
    (dem_dir / "alti3d.vrt").write_text("<VRTDataset></VRTDataset>")
    results = run_all_checks(project_root=tmp_path)
    dem_check = next(r for r in results if r.name == "DEM data")
    assert dem_check.ok is True


def test_check_tlm_data_true_when_config_references_external_path(tmp_path):
    config_dir = tmp_path / "pipeline" / "config"
    config_dir.mkdir(parents=True)
    external_tlm = tmp_path / "shared" / "swissTLM3D.gpkg"
    external_tlm.parent.mkdir(parents=True)
    external_tlm.write_text("fake gpkg content")
    config = {
        "name": "my_map",
        "source_data": {
            "tlm": str(external_tlm.relative_to(tmp_path)),
            "dem": "data/my_map/alti3d.vrt",
        },
    }
    (config_dir / "my_map.json").write_text(json.dumps(config))

    from system_checks import check_tlm_data
    result = check_tlm_data(project_root=tmp_path)
    assert result.ok is True


def test_check_tlm_data_false_when_no_data_and_no_config(tmp_path):
    from system_checks import check_tlm_data
    result = check_tlm_data(project_root=tmp_path)
    assert result.ok is False
