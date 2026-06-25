# pipeline/tests/test_e2e.py
"""End-to-end pipeline test using the example config.

Does not require GDAL, Blender, or swisstopo data.
All steps fall back gracefully when tools are unavailable.
"""
import sys, json, shutil, subprocess
from pathlib import Path
import pytest

PIPELINE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PIPELINE_DIR))

CONFIG_PATH = str(PIPELINE_DIR / "config" / "example.json")
# output_dir() returns Path("maps") / name — relative to CWD of subprocess,
# which is PIPELINE_DIR (scripts are invoked from there via absolute paths,
# but the relative "maps/" resolves against CWD at time of mkdir).
# run_pipeline.py and individual scripts run with the shell CWD inherited
# from the test process, which is PIPELINE_DIR when pytest is invoked from there.
# We force CWD=PIPELINE_DIR in subprocess calls so output is predictable.
OUTPUT_DIR = PIPELINE_DIR / "maps" / "test_area"


@pytest.fixture(autouse=True)
def clean_output():
    """Remove test output before and after each test."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    yield
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)


def run_script(script_name: str) -> int:
    script = PIPELINE_DIR / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script), CONFIG_PATH],
        capture_output=True, text=True,
        cwd=str(PIPELINE_DIR),
    )
    return result.returncode


def test_reproject_runs_without_error():
    assert run_script("01_reproject.py") == 0


def test_terrain_produces_output_file():
    run_script("01_reproject.py")
    run_script("02_terrain.py")
    glb = OUTPUT_DIR / "terrain.glb"
    assert glb.exists(), f"terrain.glb not found at {glb}"
    assert glb.stat().st_size > 0


def test_roads_produces_output_file():
    run_script("01_reproject.py")
    run_script("03_roads.py")
    glb = OUTPUT_DIR / "roads.glb"
    assert glb.exists()
    assert glb.stat().st_size > 0


def test_buildings_produces_output_file():
    run_script("01_reproject.py")
    run_script("04_buildings.py")
    glb = OUTPUT_DIR / "buildings.glb"
    assert glb.exists()
    assert glb.stat().st_size > 0


def test_vegetation_produces_valid_json():
    run_script("01_reproject.py")
    run_script("05_vegetation.py")
    veg = OUTPUT_DIR / "vegetation.json"
    assert veg.exists()
    data = json.loads(veg.read_text())
    assert "positions" in data
    assert isinstance(data["positions"], list)


def test_road_graph_produces_valid_json():
    run_script("01_reproject.py")
    run_script("06_road_graph.py")
    graph = OUTPUT_DIR / "road-graph.json"
    assert graph.exists()
    data = json.loads(graph.read_text())
    assert "nodes" in data
    assert "edges" in data


def test_manifest_produces_valid_json_with_required_keys():
    run_script("01_reproject.py")
    run_script("07_manifest.py")
    manifest = OUTPUT_DIR / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text())
    for key in ["name", "displayName", "spawnPosition", "startLine",
                "finishLine", "assets", "roadGraph", "bounds"]:
        assert key in data, f"Missing key in manifest: {key}"


def test_full_pipeline_via_orchestrator():
    result = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / "run_pipeline.py"), CONFIG_PATH],
        capture_output=True, text=True,
        cwd=str(PIPELINE_DIR),
    )
    assert result.returncode == 0, f"Pipeline failed:\n{result.stdout}\n{result.stderr}"

    expected = ["terrain.glb", "roads.glb", "buildings.glb", "vegetation.json",
                "road-graph.json", "manifest.json"]
    for fname in expected:
        assert (OUTPUT_DIR / fname).exists(), f"Missing: {fname}"
