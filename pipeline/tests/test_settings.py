# pipeline/tests/test_settings.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from settings import load_settings, save_settings


def test_load_settings_missing_file_returns_defaults(tmp_path):
    settings_path = tmp_path / ".settings.json"
    result = load_settings(settings_path)
    assert result == {"tlm_path": ""}


def test_save_and_load_roundtrip(tmp_path):
    settings_path = tmp_path / ".settings.json"
    save_settings(settings_path, {"tlm_path": "/data/swissTLM3D.gpkg"})
    result = load_settings(settings_path)
    assert result["tlm_path"] == "/data/swissTLM3D.gpkg"


def test_load_settings_corrupt_file_returns_defaults(tmp_path):
    settings_path = tmp_path / ".settings.json"
    settings_path.write_text("not valid json")
    result = load_settings(settings_path)
    assert result == {"tlm_path": ""}
