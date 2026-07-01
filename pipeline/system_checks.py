# pipeline/system_checks.py
"""Single implementation of every "is my machine set up?" check. Replaces
the duplicated logic previously in check_system.sh, check_system.ps1, and
setup-guide/steps.js."""
from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    fix_macos: str = ""
    fix_windows: str = ""


def check_command(cmd: str, name: str, fix_macos: str = "", fix_windows: str = "") -> CheckResult:
    found = shutil.which(cmd) is not None
    return CheckResult(name=name, ok=found, fix_macos=fix_macos, fix_windows=fix_windows)


def check_python312() -> CheckResult:
    for cmd in ("python3.12", "py"):
        exe = shutil.which(cmd)
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
    found = shutil.which("gdal-config") is not None or platform.system() == "Windows"
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


def check_dem_data(project_root: Path) -> CheckResult:
    found = any((project_root / "data").glob("*/alti3d.vrt")) if (project_root / "data").exists() else False
    return CheckResult(
        name="DEM data", ok=found,
        fix_macos="Download swissALTI3D tiles into data/<map_name>/ (see New Map screen)",
        fix_windows="Download swissALTI3D tiles into data\\<map_name>\\ (see New Map screen)",
    )


def check_tlm_data(project_root: Path) -> CheckResult:
    data_dir = project_root / "data"
    found = any(data_dir.glob("*/*.gpkg")) if data_dir.exists() else False
    return CheckResult(
        name="TLM data", ok=found,
        fix_macos="Download swissTLM3D and set its path on the New Map screen",
        fix_windows="Download swissTLM3D and set its path on the New Map screen",
    )


def check_config(project_root: Path) -> CheckResult:
    config_dir = project_root / "pipeline" / "config"
    found = any(
        p.stem != "example" for p in config_dir.glob("*.json")
    ) if config_dir.exists() else False
    return CheckResult(
        name="Map config", ok=found,
        fix_macos="Use the New Map screen to create one",
        fix_windows="Use the New Map screen to create one",
    )


def run_all_checks(project_root: Path) -> list[CheckResult]:
    checks = [
        check_python312(),
        check_gdal_system(),
        check_venv(project_root),
        check_deps(project_root),
        check_blender(),
        check_gltfpack(),
        check_dem_data(project_root),
        check_tlm_data(project_root),
        check_config(project_root),
    ]
    if platform.system() == "Darwin":
        checks.insert(0, check_command(
            "brew", "Homebrew", fix_macos="See https://brew.sh"
        ))
    return checks
