# Pipeline Setup Guide — macOS

> **Prefer a visual guide?** Open [`pipeline/setup-guide/index.html`](setup-guide/index.html) in your browser for an interactive step-by-step walkthrough.

From a clean macOS installation to a working pipeline. Follow every step in order.

> **Windows?** See [SETUP_WINDOWS.md](SETUP_WINDOWS.md).

---

## 1. Install Homebrew

Homebrew is the package manager used to install all system dependencies.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions. At the end it will print two commands to add Homebrew to your PATH — run those too. They look like:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
```

---

## 2. Install Python 3.12

Python 3.14 (the macOS default as of mid-2026) is too new — GDAL binary wheels are only available for 3.10–3.12.

```bash
brew install python@3.12
```

Verify:

```bash
python3.12 --version
# Python 3.12.x
```

> You do not need to change your system default Python. All commands below use `python3.12` explicitly.

---

## 3. Install GDAL (system library)

The `gdal` Python package is a wrapper around the native GDAL C library. The library must be installed first.

```bash
brew install gdal
```

Verify:

```bash
gdal-config --version
# 3.x.x
```

---

## 4. Create a virtual environment

Keep pipeline dependencies isolated from your system Python.

```bash
cd /path/to/Brelly
python3.12 -m venv .venv
source .venv/bin/activate
```

Your prompt will now show `(.venv)`. All `pip` and `python` commands below run inside this environment.

> To deactivate later: `deactivate`  
> To reactivate in a new terminal: `source .venv/bin/activate`

---

## 5. Install Python dependencies

```bash
pip install -r pipeline/requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `gdal` | Read GeoTIFF and GeoPackage files |
| `pyproj` | Coordinate reference system transforms |
| `shapely` | Geometry operations |
| `numpy` | Array math |
| `pytest` | Test suite |

If `gdal` fails, pin the version to match the system library:

```bash
pip install gdal==$(gdal-config --version) pyproj shapely numpy pytest
```

Verify all packages:

```bash
python -c "from osgeo import gdal; print(gdal.__version__)"
python -c "import pyproj, shapely, numpy; print('OK')"
```

---

## 6. Install Blender

Blender is used to bake 3-D meshes for terrain, roads, and buildings.

Download from https://www.blender.org/download/ and install the `.dmg` as usual.

Then make the `blender` command available on your PATH:

```bash
echo 'export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:

```bash
blender --version
# Blender 4.x.x
```

> Without Blender, steps 02–04 write empty placeholder GLB files. The pipeline still runs — you just get no terrain/road/building geometry.

---

## 7. Install gltfpack (optional)

gltfpack compresses `.glb` files in step 08. Skip if you do not need compressed output.

```bash
brew install meshoptimizer
```

Verify:

```bash
gltfpack --version
```

> If `brew` does not find it, download a prebuilt binary from https://github.com/zeux/meshoptimizer/releases and place it somewhere on your PATH (e.g. `/usr/local/bin/gltfpack`).

---

## 8. Download source data

The pipeline needs two datasets from swisstopo. Both are free to download.

### alti3D (digital elevation model)

1. Go to https://www.swisstopo.admin.ch/en/height-model-swissalti3d
2. Download the GeoTIFF for your area of interest (0.5 m resolution, LV95).
3. Save as e.g. `data/alti3d.tif` relative to the project root.

### swissTLM3D (topographic landscape model)

1. Go to https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d
2. Download the GeoPackage (`.gpkg`) — choose the full dataset or a regional extract.
3. Save as e.g. `data/swissTLM3D.gpkg` relative to the project root.

Your `data/` folder should look like:

```
Brelly/
└── data/
    ├── alti3d.tif
    └── swissTLM3D.gpkg
```

---

## 9. Create a map config

Copy the example config and edit it for your area:

```bash
cp pipeline/config/example.json pipeline/config/my_area.json
```

Open `pipeline/config/my_area.json` and set at minimum:

| Field | What to change |
|-------|---------------|
| `name` | Short identifier, no spaces (becomes the output folder name) |
| `displayName` | Human-readable name |
| `center_e` | LV95 easting of the centre of your map area |
| `center_n` | LV95 northing |
| `radius_m` | Half-width of the area in metres (500 = 1 km × 1 km) |
| `base_elevation` | Approximate ground elevation at the centre in metres |
| `source_data.dem` | Path to your alti3D GeoTIFF |
| `source_data.tlm` | Path to your swissTLM3D GeoPackage |

To find LV95 coordinates for a location, use the swisstopo map viewer at https://map.geo.admin.ch — right-click any point to copy coordinates.

---

## 10. Run the pipeline

Make sure the virtual environment is active (`source .venv/bin/activate`), then:

```bash
python pipeline/run_pipeline.py pipeline/config/my_area.json
```

You will see output like:

```
============================================================
Running: scripts/01_reproject.py
============================================================
Reprojected data clipped to bbox → maps/my_area/reprojected.gpkg

============================================================
Running: scripts/02_terrain.py
============================================================
Terrain GLB → maps/my_area/terrain.glb
...
Pipeline complete.
```

Output lands in `maps/my_area/`:

```
maps/my_area/
├── terrain.glb
├── roads.glb
├── buildings.glb
├── vegetation.json
├── road-graph.json
└── manifest.json
```

---

## 11. Run the tests

```bash
pytest pipeline/tests/
```

All tests should pass with or without GDAL and Blender installed.

---

## Troubleshooting

### `command not found: pip`

Use `pip3` or the explicit form:

```bash
python3.12 -m pip install -r pipeline/requirements.txt
```

### `FileNotFoundError: gdal-config`

System GDAL is not installed. Run:

```bash
brew install gdal
```

Then retry the pip install.

### `gdal` pip install fails on Python 3.14+

Python 3.14 has no prebuilt GDAL wheels. Use Python 3.12:

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements.txt
```

### `WARNING: Blender not found`

Blender is not on your PATH. Either follow step 6, or run:

```bash
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"
```

This is temporary (current terminal only). Add the line to `~/.zprofile` to make it permanent.

### `WARNING: TLM source not found`

The path in `source_data.tlm` does not point to an existing file. Check the path in your config JSON — it is relative to where you run the script from (the project root).

### `WARNING: gltfpack not found`

gltfpack is optional. If you want compression, install it via `brew install meshoptimizer`. Otherwise ignore the warning — output GLBs are uncompressed but valid.

### `FAILED: scripts/XX_*.py exited with code N`

The pipeline stops at the first failing step. Check the lines immediately above the `FAILED:` line for the specific error. Fix it, then re-run — the orchestrator always starts from step 01.
