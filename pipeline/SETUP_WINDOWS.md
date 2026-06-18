# Pipeline Setup Guide — Windows

> **Prefer a visual guide?** Open [`pipeline/setup-guide/index.html`](setup-guide/index.html) in your browser for an interactive step-by-step walkthrough.

From a clean Windows installation to a working pipeline. Follow every step in order.

All commands run in **PowerShell** unless noted otherwise. Open it by pressing `Win + X` → "Windows PowerShell" or "Terminal".

> **macOS?** See [SETUP_MACOS.md](SETUP_MACOS.md).

---

## 1. Install Python 3.12

Python 3.14+ is too new — GDAL binary wheels are only available for 3.10–3.12.

1. Go to https://www.python.org/downloads/release/python-3128/ (or the latest 3.12.x)
2. Download **Windows installer (64-bit)**
3. Run the installer — **check "Add python.exe to PATH"** before clicking Install

Verify in a new PowerShell window:

```powershell
python --version
# Python 3.12.x
```

> If you see 3.13+ or nothing, the PATH was not set. Re-run the installer, choose "Modify", and tick "Add Python to environment variables".

---

## 2. Install GDAL (system library)

The `gdal` Python package on Windows requires pre-built binaries from Christoph Gohlke's repository. The standard `pip install gdal` **does not work on Windows** — skip it.

Install via the unofficial wheels:

```powershell
pip install gdal --find-links https://github.com/cgohlke/geospatial-wheels/releases
```

If that fails, download the `.whl` manually:

1. Go to https://github.com/cgohlke/geospatial-wheels/releases
2. Find the latest release, download the file matching your Python version — e.g. `GDAL-3.x.x-cp312-cp312-win_amd64.whl`
3. Install it:

```powershell
pip install C:\Users\you\Downloads\GDAL-3.x.x-cp312-cp312-win_amd64.whl
```

Verify:

```powershell
python -c "from osgeo import gdal; print(gdal.__version__)"
```

---

## 3. Create a virtual environment

Keep pipeline dependencies isolated from your system Python.

```powershell
cd C:\path\to\Brelly
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your prompt will now show `(.venv)`. All `pip` and `python` commands below run inside this environment.

> If you get an error about execution policy, run this first (once):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

> To deactivate later: `deactivate`  
> To reactivate in a new terminal: `.venv\Scripts\Activate.ps1`

---

## 4. Install Python dependencies

Because GDAL is already installed (step 2), install the remaining packages and skip gdal from requirements:

```powershell
pip install pyproj shapely numpy pytest
```

Verify:

```powershell
python -c "from osgeo import gdal; print(gdal.__version__)"
python -c "import pyproj, shapely, numpy; print('OK')"
```

---

## 5. Install Blender

Blender is used to bake 3-D meshes for terrain, roads, and buildings.

1. Go to https://www.blender.org/download/
2. Download the Windows installer (`.msi`) and run it
3. Default install path: `C:\Program Files\Blender Foundation\Blender 4.x\`

Add Blender to your PATH so the pipeline can find it:

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to **Advanced** → **Environment Variables**
3. Under **User variables**, select `Path` → **Edit** → **New**
4. Add: `C:\Program Files\Blender Foundation\Blender 4.x` (match your actual version folder)
5. Click OK on all dialogs

Open a **new** PowerShell window and verify:

```powershell
blender --version
# Blender 4.x.x
```

> Without Blender, steps 02–04 write empty placeholder GLB files. The pipeline still runs — you just get no terrain/road/building geometry.

---

## 6. Install gltfpack (optional)

gltfpack compresses `.glb` files in step 08. Skip if you do not need compressed output.

1. Go to https://github.com/zeux/meshoptimizer/releases
2. Download `gltfpack-win64.exe` from the latest release
3. Rename it to `gltfpack.exe` and place it in a folder on your PATH, e.g. `C:\tools\`
4. Add `C:\tools` to your PATH using the same steps as for Blender above

Verify in a new PowerShell window:

```powershell
gltfpack --version
```

---

## 7. Download source data

The pipeline needs two datasets from swisstopo. Both are free to download.

### alti3D (digital elevation model)

1. Go to https://www.swisstopo.admin.ch/en/height-model-swissalti3d
2. Download the GeoTIFF for your area of interest (0.5 m resolution, LV95)
3. Save as e.g. `data\alti3d.tif` relative to the project root

### swissTLM3D (topographic landscape model)

1. Go to https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d
2. Download the GeoPackage (`.gpkg`) — choose the full dataset or a regional extract
3. Save as e.g. `data\swissTLM3D.gpkg` relative to the project root

Your `data\` folder should look like:

```
Brelly\
└── data\
    ├── alti3d.tif
    └── swissTLM3D.gpkg
```

---

## 8. Create a map config

Copy the example config and edit it for your area:

```powershell
copy pipeline\config\example.json pipeline\config\my_area.json
```

Open `pipeline\config\my_area.json` in any text editor and set at minimum:

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

Use forward slashes or escaped backslashes in paths inside the JSON:

```json
"source_data": {
  "dem": "data/alti3d.tif",
  "tlm": "data/swissTLM3D.gpkg"
}
```

To find LV95 coordinates for a location, use the swisstopo map viewer at https://map.geo.admin.ch — right-click any point to copy coordinates.

---

## 9. Run the pipeline

Make sure the virtual environment is active (`.venv\Scripts\Activate.ps1`), then:

```powershell
python pipeline\run_pipeline.py pipeline\config\my_area.json
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

Output lands in `maps\my_area\`:

```
maps\my_area\
├── terrain.glb
├── roads.glb
├── buildings.glb
├── vegetation.json
├── road-graph.json
└── manifest.json
```

---

## 10. Run the tests

```powershell
pytest pipeline\tests\
```

All tests should pass with or without GDAL and Blender installed.

---

## Troubleshooting

### `python` is not recognised

Python was not added to PATH during install. Re-run the installer, choose "Modify", and tick "Add Python to environment variables". Then open a new PowerShell window.

### `pip install gdal` fails

Do not use the standard PyPI `gdal` package on Windows — it requires compiling from source. Use the pre-built wheel from Gohlke's repo as described in step 2.

### `from osgeo import gdal` fails after installing the wheel

The wheel CPU architecture must match your system. Ensure you downloaded `win_amd64` (64-bit) and that your Python is also 64-bit (`python -c "import struct; print(struct.calcsize('P')*8)"`).

### PowerShell says "running scripts is disabled"

Run once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `WARNING: Blender not found`

Blender is not on your PATH. Follow step 5, then open a **new** PowerShell window (PATH changes do not apply to already-open windows).

### `WARNING: TLM source not found`

The path in `source_data.tlm` does not point to an existing file. Check the path in your config JSON — it is relative to the project root (where you run the script from). Use forward slashes.

### `WARNING: gltfpack not found`

gltfpack is optional. If you want compression, follow step 6. Otherwise ignore the warning — output GLBs are uncompressed but valid.

### `FAILED: scripts/XX_*.py exited with code N`

The pipeline stops at the first failing step. Check the lines immediately above the `FAILED:` line for the specific error. Fix it, then re-run — the orchestrator always starts from step 01.
