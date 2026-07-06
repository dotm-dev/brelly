import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

spec = importlib.util.spec_from_file_location(
    "beamng_roads_step", Path(__file__).parent.parent / "scripts" / "01_roads.py"
)
roads_step = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roads_step)


def _write_config(tmp_path: Path) -> Path:
    config = {"name": "test_area"}
    config_path = tmp_path / "test_area.json"
    config_path.write_text(json.dumps(config))
    return config_path


def test_main_raises_when_splines_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_config(tmp_path)
    with pytest.raises(FileNotFoundError):
        roads_step.main(str(config_path))


def test_main_converts_splines_to_decalroads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_config(tmp_path)

    maps_dir = tmp_path / "maps" / "test_area"
    maps_dir.mkdir(parents=True)
    splines = [
        {
            "id": "r1",
            "roadType": "road_local",
            "widthMetres": 6.0,
            "nodes": [
                {"x": 0.0, "y": 0.0, "z": 0.0, "isLocked": True},
                {"x": 10.0, "y": 0.5, "z": -20.0, "isLocked": False},
            ],
            "segments": [],
        }
    ]
    (maps_dir / "road_splines.json").write_text(json.dumps(splines))

    roads_step.main(str(config_path))

    objs_path = maps_dir / "beamng" / "test_area" / "_road_objects.json"
    objs = json.loads(objs_path.read_text())
    assert len(objs) == 1
    assert objs[0]["class"] == "DecalRoad"
    assert objs[0]["nodes"] == [[0.0, 0.0, 0.0, 6.0], [10.0, 20.0, 0.5, 6.0]]


def test_main_skips_single_node_roads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_config(tmp_path)
    maps_dir = tmp_path / "maps" / "test_area"
    maps_dir.mkdir(parents=True)
    splines = [{"id": "r1", "widthMetres": 4.0, "nodes": [{"x": 0, "y": 0, "z": 0, "isLocked": True}]}]
    (maps_dir / "road_splines.json").write_text(json.dumps(splines))

    roads_step.main(str(config_path))

    objs_path = maps_dir / "beamng" / "test_area" / "_road_objects.json"
    assert json.loads(objs_path.read_text()) == []
