# pipeline/tests/test_app.py
import sys
import json
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import scan_configs, build_run_config


def test_scan_configs_finds_json(tmp_path):
    (tmp_path / "bre.json").write_text('{"name": "bre"}')
    (tmp_path / "alps.json").write_text('{"name": "alps"}')
    results = scan_configs(tmp_path)
    names = [r[0] for r in results]
    assert "bre" in names
    assert "alps" in names
    assert names == sorted(names)


def test_scan_configs_excludes_example(tmp_path):
    (tmp_path / "example.json").write_text('{"name": "example"}')
    (tmp_path / "bre.json").write_text('{"name": "bre"}')
    results = scan_configs(tmp_path)
    names = [r[0] for r in results]
    assert "example" not in names
    assert "bre" in names


def test_scan_configs_uses_name_field(tmp_path):
    (tmp_path / "mymap.json").write_text('{"name": "Custom Name"}')
    results = scan_configs(tmp_path)
    assert results[0][0] == "Custom Name"


def test_scan_configs_falls_back_to_stem(tmp_path):
    (tmp_path / "mymap.json").write_text('{}')
    results = scan_configs(tmp_path)
    assert results[0][0] == "mymap"


def test_build_run_config_overrides_skip_steps(tmp_path):
    cfg = {"name": "bre", "skip_steps": [], "other": 42}
    cfg_path = tmp_path / "bre.json"
    cfg_path.write_text(json.dumps(cfg))
    out_path = tmp_path / "out.json"
    build_run_config(cfg_path, {"terrain", "roads"}, out_path)
    result = json.loads(out_path.read_text())
    assert set(result["skip_steps"]) == {"terrain", "roads"}
    assert result["other"] == 42
    assert result["name"] == "bre"


def test_build_run_config_empty_skip(tmp_path):
    cfg = {"name": "bre", "skip_steps": ["old"]}
    cfg_path = tmp_path / "bre.json"
    cfg_path.write_text(json.dumps(cfg))
    out_path = tmp_path / "out.json"
    build_run_config(cfg_path, set(), out_path)
    result = json.loads(out_path.read_text())
    assert result["skip_steps"] == []
