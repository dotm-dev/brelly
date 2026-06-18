# Pipeline Setup Guide — Windows

> **Prefer a visual guide?** Open [`pipeline/setup-guide/index.html`](setup-guide/index.html) in your browser for an interactive step-by-step walkthrough.

> **macOS?** See [SETUP_MACOS.md](SETUP_MACOS.md).

All commands run in **PowerShell** (`Win + X` → Terminal).

---

## 1. Install Python 3.12

GDAL wheels are only available for 3.10–3.12 — 3.14+ won't work.

1. Download from https://www.python.org/downloads/release/python-3128/ (Windows installer, 64-bit)
2. Run — **check "Add python.exe to PATH"** before clicking Install

```powershell
python --version   # Python 3.12.x
```

> PATH not set? Re-run the installer → Modify → tick "Add Python to environment variables".

## 2. Install GDAL

Standard `pip install gdal` doesn't work on Windows — use Gohlke's prebuilt wheels:

```powershell
pip install gdal --find-links https://github.com/cgohlke/geospatial-wheels/releases
```

If that fails, download `GDAL-3.x.x-cp312-cp312-win_amd64.whl` manually from https://github.com/cgohlke/geospatial-wheels/releases and:

```powershell
pip install C:\Users\you\Downloads\GDAL-3.x.x-cp312-cp312-win_amd64.whl
```

Verify:

```powershell
python -c "from osgeo import gdal; print(gdal.__version__)"
```

## 3. Create a virtual environment

```powershell
cd C:\path\to\Brelly
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> Execution policy error? Run once: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

Reactivate in a new terminal: `.venv\Scripts\Activate.ps1`

## 4. Install Python dependencies

GDAL is already installed (step 2), so skip it here:

```powershell
pip install pyproj shapely numpy pytest
```

Verify:

```powershell
python -c "import pyproj, shapely, numpy; print('OK')"
```

## 5. Install Blender

1. Download from https://www.blender.org/download/ (`.msi`) and install
2. Add to PATH: `Win + R` → `sysdm.cpl` → Advanced → Environment Variables → User `Path` → Edit → New → add `C:\Program Files\Blender Foundation\Blender 4.x`

Open a new PowerShell window:

```powershell
blender --version   # Blender 4.x.x
```

> Without Blender, steps 02–04 produce empty placeholder GLBs.

## 6. Install gltfpack (optional)

Compresses `.glb` output. Skip if you don't need it.

1. Download `gltfpack-win64.exe` from https://github.com/zeux/meshoptimizer/releases
2. Rename to `gltfpack.exe`, place in e.g. `C:\tools\`, add that folder to PATH (same steps as Blender above)

```powershell
gltfpack --version
```

## 7. Download source data

Both datasets are free from swisstopo.

- **alti3D** (DEM): https://www.swisstopo.admin.ch/en/height-model-swissalti3d — download GeoTIFF (0.5 m, LV95), save as `data\alti3d.tif`
- **swissTLM3D**: https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d — download GeoPackage, save as `data\swissTLM3D.gpkg`

## 8. Create a map config

```powershell
copy pipeline\config\example.json pipeline\config\my_area.json
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

Use forward slashes or escaped backslashes in JSON paths. Find LV95 coordinates: https://map.geo.admin.ch — right-click any point.

## 9. Run the pipeline

```powershell
python pipeline\run_pipeline.py pipeline\config\my_area.json
```

Output lands in `maps\my_area\`.

## 10. Run the tests

```powershell
pytest pipeline\tests\
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `python` not recognised | Re-run installer → Modify → tick "Add Python to environment variables" |
| `pip install gdal` fails | Use Gohlke wheels (step 2) |
| `from osgeo import gdal` fails after wheel install | Ensure you installed `win_amd64` and Python is 64-bit |
| Scripts disabled in PowerShell | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `WARNING: Blender not found` | Add Blender to PATH (step 5), open a new terminal |
| `WARNING: TLM source not found` | Check `source_data.tlm` path in config — relative to project root, forward slashes |
| `WARNING: gltfpack not found` | Optional — install via step 6 or ignore |
| `FAILED: scripts/XX_*.py exited with code N` | Read the lines above the error |
