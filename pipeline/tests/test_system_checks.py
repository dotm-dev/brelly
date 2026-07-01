# pipeline/tests/test_system_checks.py
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
