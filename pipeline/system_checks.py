# pipeline/system_checks.py
"""Single implementation of every "is my machine set up?" check. Replaces
the duplicated logic previously in check_system.sh, check_system.ps1, and
setup-guide/steps.js."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    fix_macos: str = ""
    fix_windows: str = ""


# Homebrew only updates PATH for shells that freshly source your profile —
# a terminal already open when brew (or something brew installed) shows up
# won't see /opt/homebrew/bin yet, even though it's really there. Fall back
# to checking Homebrew's known bin dirs directly so System Check doesn't
# report false negatives just because of terminal/PATH staleness.
_HOMEBREW_BIN_DIRS = (Path("/opt/homebrew/bin"), Path("/usr/local/bin"))


def which(cmd: str) -> str | None:
    found = shutil.which(cmd)
    if found:
        return found
    if platform.system() != "Darwin":
        return None
    for bin_dir in _HOMEBREW_BIN_DIRS:
        candidate = bin_dir / cmd
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def check_command(cmd: str, name: str, fix_macos: str = "", fix_windows: str = "") -> CheckResult:
    found = which(cmd) is not None
    return CheckResult(name=name, ok=found, fix_macos=fix_macos, fix_windows=fix_windows)


def check_python312() -> CheckResult:
    for cmd in ("python3.12", "py"):
        exe = which(cmd)
        if not exe:
            continue
        try:
            args = [exe, "-3.12", "--version"] if cmd == "py" else [exe, "--version"]
            subprocess.run(args, capture_output=True, check=True, timeout=5)
            return CheckResult(name="Python 3.12", ok=True)
        except (subprocess.CalledProcessError, OSError):
            continue
    return CheckResult(
        name="Python 3.12",
        ok=False,
        fix_macos="brew install python@3.12",
        fix_windows="winget install Python.Python.3.12",
    )


def check_gdal_system() -> CheckResult:
    found = which("gdal-config") is not None or platform.system() == "Windows"
    return CheckResult(
        name="GDAL system library",
        ok=found,
        fix_macos="brew install gdal",
        fix_windows="See pipeline/SETUP_WINDOWS.md — GDAL via OSGeo4W",
    )


def _venv_python(project_root: Path) -> Path:
    if platform.system() == "Windows":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python3"


def check_venv(project_root: Path) -> CheckResult:
    exe = _venv_python(project_root)
    return CheckResult(
        name="Virtual environment",
        ok=exe.exists(),
        fix_macos="python3.12 -m venv .venv",
        fix_windows="py -3.12 -m venv .venv",
    )


def check_deps(project_root: Path) -> CheckResult:
    exe = _venv_python(project_root)
    if not exe.exists():
        return CheckResult(name="Python dependencies", ok=False,
                            fix_macos="source .venv/bin/activate && pip install -r pipeline/requirements.txt",
                            fix_windows=".venv\\Scripts\\activate && pip install -r pipeline\\requirements.txt")
    try:
        subprocess.run(
            [str(exe), "-c", "from osgeo import gdal; import pyproj, shapely, numpy"],
            capture_output=True, check=True, timeout=10,
        )
        return CheckResult(name="Python dependencies", ok=True)
    except (subprocess.CalledProcessError, OSError):
        return CheckResult(
            name="Python dependencies", ok=False,
            fix_macos="source .venv/bin/activate && pip install -r pipeline/requirements.txt",
            fix_windows=".venv\\Scripts\\activate && pip install -r pipeline\\requirements.txt",
        )


def check_blender() -> CheckResult:
    return check_command(
        "blender", "Blender",
        fix_macos="brew install --cask blender",
        fix_windows="winget install BlenderFoundation.Blender",
    )


def check_gltfpack() -> CheckResult:
    return check_command(
        "gltfpack", "gltfpack",
        fix_macos="brew install gltfpack  # or build from https://github.com/zeux/meshoptimizer",
        fix_windows="Download from https://github.com/zeux/meshoptimizer/releases",
    )


def map_data_ready(config_path: Path, project_root: Path) -> CheckResult:
    """Per-map data readiness: does this specific config's source_data.dem
    and source_data.tlm both resolve to an existing file? Used by the Run
    tab to flag individual maps, not a global "does any map have data"
    check — with multiple maps that global version is nearly meaningless."""
    name = config_path.stem
    try:
        data = json.loads(config_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return CheckResult(name=name, ok=False, detail="Config file is invalid.")

    source = data.get("source_data", {})
    missing = []
    for key, label in (("dem", "DEM"), ("tlm", "TLM")):
        path_str = source.get(key)
        if not path_str or not (project_root / path_str).exists():
            missing.append(label)

    if missing:
        return CheckResult(name=name, ok=False, detail=f"Missing {' and '.join(missing)} data")
    return CheckResult(name=name, ok=True)


# If you add a new installable dependency check here, also update the
# matching install step in pipeline/setup.sh and pipeline/setup.ps1 — they
# hand-implement install logic for these checks and won't pick up new
# entries automatically.
_CHECK_FUNCS: dict[str, Callable[[Path], CheckResult]] = {
    "Homebrew": lambda root: check_command("brew", "Homebrew", fix_macos="See https://brew.sh"),
    "Python 3.12": lambda root: check_python312(),
    "GDAL system library": lambda root: check_gdal_system(),
    "Virtual environment": check_venv,
    "Python dependencies": check_deps,
    "Blender": lambda root: check_blender(),
    "gltfpack": lambda root: check_gltfpack(),
}


def run_single_check(name: str, project_root: Path) -> CheckResult:
    """Re-run one named check by its CheckResult.name (see run_all_checks
    for the full ordered set). Raises KeyError for an unknown name."""
    return _CHECK_FUNCS[name](project_root)


def run_all_checks(project_root: Path) -> list[CheckResult]:
    checks = [
        check_python312(),
        check_gdal_system(),
        check_venv(project_root),
        check_deps(project_root),
        check_blender(),
        check_gltfpack(),
    ]
    if platform.system() == "Darwin":
        checks.insert(0, check_command(
            "brew", "Homebrew", fix_macos="See https://brew.sh"
        ))
    return checks
