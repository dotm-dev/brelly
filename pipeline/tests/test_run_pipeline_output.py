# pipeline/tests/test_run_pipeline_output.py
"""Regression coverage for run_pipeline.py's progress output: the
cursor-up/clear-line overwrite trick only makes sense on a real terminal.
Piped output (e.g. the Run tab's log pane) must get plain, non-duplicated
lines instead."""
import json
import sys
import types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import run_pipeline


def _write_config(tmp_path: Path) -> Path:
    skip_all_but_one = [label for label, _script in run_pipeline.SCRIPTS[1:]]
    config = {
        "name": "test_map", "displayName": "Test Map",
        "skip_steps": skip_all_but_one,
    }
    config_path = tmp_path / "test_map.json"
    config_path.write_text(json.dumps(config))
    return config_path


def _fake_subprocess_run(*_args, **_kwargs):
    return types.SimpleNamespace(returncode=0, stdout="", stderr="")


def test_run_uses_plain_lines_when_not_a_tty(tmp_path, monkeypatch, capsys):
    config_path = _write_config(tmp_path)
    monkeypatch.setattr(run_pipeline.subprocess, "run", _fake_subprocess_run)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    run_pipeline.run(str(config_path))

    out = capsys.readouterr().out
    assert "\x1b[" not in out, "ANSI escape codes leaked into non-tty output"
    assert "download …" in out
    assert "download  done (" in out


def test_run_uses_overwrite_escape_when_tty(tmp_path, monkeypatch, capsys):
    config_path = _write_config(tmp_path)
    monkeypatch.setattr(run_pipeline.subprocess, "run", _fake_subprocess_run)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    run_pipeline.run(str(config_path))

    out = capsys.readouterr().out
    assert "\x1b[1A\x1b[2K" in out
