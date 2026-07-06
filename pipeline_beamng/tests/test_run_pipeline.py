import sys
import types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import run_beamng_pipeline


def test_run_invokes_steps_in_order(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, check):
        calls.append(Path(cmd[1]).name)
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(run_beamng_pipeline.subprocess, "run", fake_run)
    config_path = tmp_path / "test_area.json"
    config_path.write_text("{}")

    run_beamng_pipeline.run(str(config_path))

    assert calls == ["00_terrain.py", "01_roads.py", "02_package.py"]


def test_run_stops_on_first_failure(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, check):
        calls.append(Path(cmd[1]).name)
        returncode = 1 if "01_roads.py" in cmd[1] else 0
        return types.SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(run_beamng_pipeline.subprocess, "run", fake_run)
    monkeypatch.setattr(run_beamng_pipeline.sys, "exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))
    config_path = tmp_path / "test_area.json"
    config_path.write_text("{}")

    import pytest
    with pytest.raises(SystemExit):
        run_beamng_pipeline.run(str(config_path))

    assert calls == ["00_terrain.py", "01_roads.py"]
