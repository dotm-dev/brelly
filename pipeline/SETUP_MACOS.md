# Pipeline Setup Guide — macOS

> **Prefer a visual guide?** Open [`pipeline/setup-guide/index.html`](setup-guide/index.html) in your browser for an interactive step-by-step walkthrough.

> **Windows?** See [SETUP_WINDOWS.md](SETUP_WINDOWS.md).

---

## 1. Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions. Run the two PATH commands it prints at the end:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

## 2. Install Python 3.12

GDAL wheels are only available for 3.10–3.12 — 3.14+ won't work. If you already have a different Python version, that's fine — 3.12 installs alongside it.

Check what you have first:

```bash
python3 --version        # active default
python3.12 --version     # 3.12 specifically (error = not installed)
```

If `python3.12` already prints `Python 3.12.x`, skip the install below. Whatever `python3` points to is left untouched — this guide always calls `python3.12` explicitly.

```bash
brew install python@3.12
python3.12 --version   # Python 3.12.x
```

## 3. Install GDAL

```bash
brew install gdal
gdal-config --version  # 3.x.x
```

## 4. Create a virtual environment

```bash
cd /path/to/Brelly
python3.12 -m venv .venv
source .venv/bin/activate
```

Reactivate in a new terminal: `source .venv/bin/activate`

## 5. Install Python dependencies

```bash
pip install -r pipeline/requirements.txt
```

If `gdal` fails, pin it to match the system library:

```bash
pip install gdal==$(gdal-config --version) pyproj shapely numpy pytest
```

Verify:

```bash
python -c "from osgeo import gdal; print(gdal.__version__)"
python -c "import pyproj, shapely, numpy; print('OK')"
```

## 6. Install Blender

Download from https://www.blender.org/download/ and install the `.dmg`.

```bash
echo 'export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"' >> ~/.zprofile
source ~/.zprofile
blender --version   # Blender 4.x.x
```

> Without Blender, steps 02–04 produce empty placeholder GLBs.

## 7. Install gltfpack (optional)

Compresses `.glb` output. Skip if you don't need it.

No Homebrew formula exists — install the binary directly:

1. Go to https://github.com/zeux/meshoptimizer/releases
2. Download `gltfpack-macos` from the latest release

```bash
mv ~/Downloads/gltfpack /usr/local/bin/gltfpack
chmod +x /usr/local/bin/gltfpack
gltfpack --version
```

## 8. Download source data

Both datasets are free from swisstopo.

- **alti3D** (DEM): https://www.swisstopo.admin.ch/en/height-model-swissalti3d — download GeoTIFF (0.5 m, LV95), save as `data/alti3d.tif`
- **swissTLM3D**: https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d — download GeoPackage, save as `data/swissTLM3D.gpkg`

## 9. Create a map config

```bash
cp pipeline/config/example.json pipeline/config/my_area.json
```

Edit at minimum:

| Field | What to change |
|-------|---------------|
| `name` | Short identifier, no spaces |
| `displayName` | Human-readable name |
| `center_e` | LV95 easting of map centre |
| `center_n` | LV95 northing |
| `radius_m` | Half-width in metres (500 = 1 km × 1 km) |
| `base_elevation` | Approximate ground elevation in metres |
| `source_data.dem` | Path to alti3D GeoTIFF |
| `source_data.tlm` | Path to swissTLM3D GeoPackage |

Find LV95 coordinates: https://map.geo.admin.ch — right-click any point.

## 10. Run the pipeline

```bash
python pipeline/run_pipeline.py pipeline/config/my_area.json
```

Output lands in `maps/my_area/`.

## 11. Run the tests

```bash
pytest pipeline/tests/
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `command not found: pip` | `python3.12 -m pip install -r pipeline/requirements.txt` |
| `FileNotFoundError: gdal-config` | `brew install gdal`, then retry pip |
| `gdal` fails on Python 3.14+ | Use Python 3.12 (step 2) |
| `WARNING: Blender not found` | Add Blender to PATH (step 6) |
| `WARNING: TLM source not found` | Check `source_data.tlm` path in config — relative to project root |
| `WARNING: gltfpack not found` | Optional — install via step 7 or ignore |
| `FAILED: scripts/XX_*.py exited with code N` | Read the lines above the error |
