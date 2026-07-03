# Brelly

A game that places you on real Swiss terrain. This repo contains:

- **`pipeline/`** — Python pipeline that converts Swiss geodata (swisstopo DEM + TLM) into game-ready assets.
- **`src/`** — Babylon.js game engine (TypeScript).
- **`maps/`** — Output directory; one subfolder per map, consumed by the engine at runtime.

---

## Quick start

### 1. Install dependencies

Run the installer for your OS — it checks each requirement, installs
whatever's missing, and launches the app when done:

- **macOS:** `bash pipeline/setup.sh`
- **Windows:** `.\pipeline\setup.ps1`

Both install without prompting by default. Flags:

- `-i` / `-Interactive` — confirm before each install
- `-v` / `-Verbose` — stream full installer output instead of a quiet spinner

Prefer to do it by hand, or just want a status check without installing
anything? Run `python pipeline/app.py` directly — its **System Check** tab
shows the same checklist with copy-paste fix commands, without taking any
action on its own. Command references: [`pipeline/SETUP_MACOS.md`](pipeline/SETUP_MACOS.md) /
[`pipeline/SETUP_WINDOWS.md`](pipeline/SETUP_WINDOWS.md).

Requirements: Python 3.12, GDAL, Blender, Node.js

### 2. Get source data

Download from swisstopo for your area of interest:

- **swissALTI3D** (elevation) → https://www.swisstopo.admin.ch/en/height-model-swissalti3d
- **swissTLM3D** (roads, buildings, vegetation) → https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d

Place DEM tiles + a VRT index and the TLM GeoPackage under `data/<map_name>/`.

### 3. Create a map

Use the **New Map** tab in the app: give it a name, point it at your
downloaded `.tif` DEM tiles, and (once) your swissTLM3D GeoPackage. It
derives the map's centre, radius, and base elevation from the DEM extent
automatically and writes the config for you.

To edit fields by hand instead, see [`pipeline/README.md`](pipeline/README.md)
for the full config field reference.

### 4. Run the pipeline

```bash
cd /path/to/Brelly
source .venv/bin/activate
python pipeline/run_pipeline.py pipeline/config/<my_map>.json
```

Output lands in `maps/<my_map>/` — terrain, roads, buildings, vegetation, navigation graph, and a manifest.

### 5. Run the game

```bash
npm install
npm run dev
```

Open `http://localhost:5173` in a browser.

---

## Repository layout

```
Brelly/
├── pipeline/           # geodata → game assets
│   ├── run_pipeline.py # main orchestrator
│   ├── config/         # per-map JSON configs
│   ├── scripts/        # 10 processing steps (00–09)
│   ├── utils/          # shared helpers
│   └── blender/        # Blender baking scripts
├── src/                # Babylon.js game engine (TypeScript)
├── maps/               # pipeline output (git-ignored)
├── data/               # source geodata (git-ignored)
└── tests/              # pytest suite
```

---

## Pipeline overview

The pipeline runs 10 steps in order:

| Step | Script | Output |
|------|--------|--------|
| 00 | `00_download.py` | Downloads missing DEM tiles from swisstopo CSV |
| 01 | `01_reproject.py` | Clips TLM GeoPackage to the map bounding box |
| 02 | `02_terrain.py` | Builds tiled terrain mesh → `terrain.glb` |
| 03 | `03_roads.py` | Road surface meshes → `roads.glb` |
| 04 | `04_buildings.py` | Extruded building footprints → `buildings.glb` |
| 05 | `05_vegetation.py` | Tree/shrub positions → `vegetation.json` |
| 06 | `06_road_graph.py` | Navigation graph → `road-graph.json` |
| 07 | `07_manifest.py` | Engine descriptor → `manifest.json` |
| 08 | `08_lod.py` | LOD terrain meshes → `terrain_lod1.glb`, `terrain_lod2.glb` |
| 09 | `09_compress.py` | In-place GLB compression via `gltfpack` |

Full step documentation: [`pipeline/README.md`](pipeline/README.md)

---

## Running tests

```bash
source .venv/bin/activate
pytest pipeline/tests/
```

---

## Coordinate system

All pipeline output uses a local **ENU (East-North-Up)** frame centred on (`center_e`, `center_n`, `base_elevation`):

```
X = metres east  of centre
Y = metres above base_elevation
Z = metres north of centre
```
