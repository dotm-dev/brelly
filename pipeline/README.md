# Map Creation Pipeline

Converts Swiss geodata (DEM + TLM vector layers) into a self-contained map bundle ready to load in the Brelly game engine.

> **First time?** Try the [interactive setup guide](setup-guide/index.html) (open in browser) or read the text guides: [macOS](SETUP_MACOS.md) · [Windows](SETUP_WINDOWS.md)

## Output

Running the pipeline for a config named `my_area` produces:

```
maps/my_area/
├── terrain.glb        # heightmap mesh
├── roads.glb          # road surface meshes
├── buildings.glb      # extruded building footprints
├── vegetation.json    # tree/shrub point positions
├── road-graph.json    # navigation graph (nodes + edges)
└── manifest.json      # map descriptor consumed by the engine
```

---

## Configuration

Create a JSON file based on [`pipeline/config/example.json`](config/example.json):

```json
{
  "name": "test_area",
  "displayName": "Test Area",
  "center_e": 2683000,
  "center_n": 1247500,
  "radius_m": 500,
  "base_elevation": 450.0,
  "start_line": {
    "position": { "x": 0, "y": 0, "z": -50 },
    "normal":   { "x": 0, "y": 0, "z": 1 },
    "widthMetres": 12
  },
  "finish_line": {
    "position": { "x": 0, "y": 0, "z": 200 },
    "normal":   { "x": 0, "y": 0, "z": 1 },
    "widthMetres": 12
  },
  "spawn_position": { "x": 0, "y": 1,  "z": -45 },
  "spawn_rotation": { "x": 0, "y": 0,  "z": 0,   "w": 1 },
  "checkpoints": [],
  "source_data": {
    "dem": "data/my_area/alti3d.vrt",
    "tlm": "data/my_area/swissTLM3D.gpkg"
  }
}
```

### Field reference

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Machine identifier; becomes the output folder name under `maps/` |
| `displayName` | string | Human-readable label shown in the UI |
| `center_e` | number | LV95 easting of the map centre (metres) |
| `center_n` | number | LV95 northing of the map centre (metres) |
| `radius_m` | number | Half-width of the square bounding box in metres (default 500) |
| `base_elevation` | number | Ground-level elevation at origin in metres; Y=0 in ENU space |
| `start_line` | object | Race start line position, surface normal, and width |
| `finish_line` | object | Race finish line (same schema) |
| `spawn_position` | object | Player vehicle spawn point in ENU space |
| `spawn_rotation` | object | Spawn orientation as a quaternion (x, y, z, w) |
| `checkpoints` | array | Optional ordered list of checkpoint objects |
| `source_data.dem` | string | Path to the alti3D VRT mosaic (e.g. `data/my_area/alti3d.vrt`) |
| `source_data.tlm` | string | Path to the swissTLM3D GeoPackage |

### Coordinate system

All output coordinates use a **local ENU (East-North-Up)** frame centred on (`center_e`, `center_n`, `base_elevation`) in LV95:

```
X  =  metres east  of centre
Y  =  metres above base_elevation
Z  =  metres north of centre
```

The pipeline clips source data to an axis-aligned square:

```
min_e = center_e - radius_m    max_e = center_e + radius_m
min_n = center_n - radius_m    max_n = center_n + radius_m
```

---

## Running the pipeline

```bash
cd /path/to/Brelly
python pipeline/run_pipeline.py path/to/my_config.json
```

The orchestrator (`run_pipeline.py`) executes all 8 scripts in order, passes the config path to each, and exits with a non-zero code if any step fails.

To run a single step in isolation:

```bash
python pipeline/scripts/01_reproject.py path/to/my_config.json
```

---

## Pipeline steps

### Step 01 — Reproject (`01_reproject.py`)

**Input:** `source_data.tlm` (full swissTLM3D GeoPackage, LV95)  
**Output:** `maps/<name>/reprojected.gpkg`

Clips every layer in the TLM GeoPackage to the computed bounding box using a WKT polygon spatial filter (via GDAL/OGR). The output GeoPackage keeps the original LV95 CRS — no coordinate transform is applied at this stage; clipping only.

If GDAL is unavailable or the TLM file is missing, an empty GeoPackage placeholder is written so downstream steps can proceed.

**Key TLM layers consumed by later steps:**

| Layer name | Used by |
|------------|---------|
| `tlm_strassen_strasse` | steps 03, 06 |
| `tlm_bb_gebaeude` | step 04 |
| `tlm_bb_einzelbaum_gebuesch` / `tlm_einzelbaum_gebuesch` | step 05 |

---

### Step 02 — Terrain (`02_terrain.py`)

**Input:** `source_data.dem` (alti3D GeoTIFF), config  
**Output:** `maps/<name>/terrain.glb`

Loads elevation samples from the DEM and passes a heightmap JSON to Blender for mesh generation.

> **Note:** DEM sampling is not yet implemented; the step currently falls back to a flat 64×64 synthetic heightmap with `cell_size = 2.0 m` (128 m × 128 m flat plane).

**Blender baker (`blender/terrain_baker.py`):**

1. Reads `{"width": N, "height": M, "heights": [[...], ...], "cell_size": float}`.
2. Builds a grid mesh in bmesh — one quad per cell, vertices displaced by height value.
3. Centred at origin: `x = col * cell_size - (cols * cell_size / 2)`.
4. Exports with `bpy.ops.export_scene.gltf` in GLB format.

---

### Step 03 — Roads (`03_roads.py`)

**Input:** `maps/<name>/reprojected.gpkg` (layer `tlm_strassen_strasse`)  
**Output:** `maps/<name>/roads.glb`

Reads road centrelines from the clipped GeoPackage, converts each polyline vertex from LV95 to ENU, then passes a JSON array of `{"coords": [[x,y,z], ...], "width": float}` objects to Blender.

Default road width: **6.0 m** (used when the TLM feature has no width attribute).

**Blender baker (`blender/road_baker.py`):** receives the road array and produces a mesh. See [`blender/road_baker.py`](blender/road_baker.py) for mesh construction details.

---

### Step 04 — Buildings (`04_buildings.py`)

**Input:** `maps/<name>/reprojected.gpkg` (layer `tlm_bb_gebaeude` or `gebaeude`)  
**Output:** `maps/<name>/buildings.glb`

Reads polygon footprints, converts ring vertices to ENU (X, Z only — Y handled by extrusion), and passes a JSON array of:

```json
{"footprint": [[x, z], ...], "height": 8.0, "base_y": 0.0}
```

Default building height: **8.0 m**.

Only `Polygon` geometry types are processed (OGR type codes 3 and −2147483645).

**Blender baker (`blender/building_baker.py`):** extrudes each footprint polygon to the specified height. See [`blender/building_baker.py`](blender/building_baker.py) for details.

---

### Step 05 — Vegetation (`05_vegetation.py`)

**Input:** `maps/<name>/reprojected.gpkg` (layer `tlm_bb_einzelbaum_gebuesch` or `tlm_einzelbaum_gebuesch`)  
**Output:** `maps/<name>/vegetation.json`

Extracts point geometries (individual trees / shrubs). Each point is converted to ENU:

```json
{
  "positions": [
    {"x": 12.5, "y": 0.0, "z": -34.2},
    ...
  ]
}
```

`y` (elevation) uses the geometry's Z value when the feature is 3-D, otherwise falls back to `base_elevation` → `y = 0.0`.

The engine uses these positions to place instanced tree meshes at runtime — no Blender step needed.

---

### Step 06 — Road graph (`06_road_graph.py`)

**Input:** `maps/<name>/reprojected.gpkg`  
**Output:** `maps/<name>/road-graph.json`

Builds a navigation graph for AI and pathfinding:

```json
{
  "nodes": [
    {"id": "a1b2c3d4", "position": {"x": 0.0, "y": 0.0, "z": 0.0}},
    ...
  ],
  "edges": [
    {"id": "42", "fromNodeId": "a1b2c3d4", "toNodeId": "e5f6g7h8", "widthMetres": 6.0},
    ...
  ]
}
```

**Algorithm:**

1. Load road centrelines from the GeoPackage (same layer as step 03).
2. Convert start and end points of each polyline to ENU.
3. Snap nearby endpoints together with a **0.5 m grid** key (prevents duplicate nodes from floating-point jitter).
4. Assign each unique snapped position a node ID (first 8 hex chars of MD5 of the key string).
5. Each road polyline becomes one edge connecting its start-node to its end-node.

Width is read from the `OBJEKTART` field when present; defaults to **6.0 m**.

---

### Step 07 — Manifest (`07_manifest.py`)

**Input:** config JSON  
**Output:** `maps/<name>/manifest.json`

Assembles the engine-facing descriptor:

```json
{
  "name": "test_area",
  "displayName": "Test Area",
  "spawnPosition": {"x": 0, "y": 1, "z": -45},
  "spawnRotation": {"x": 0, "y": 0, "z": 0, "w": 1},
  "startLine":  { ... },
  "finishLine": { ... },
  "checkpoints": [],
  "assets": {
    "terrain":       "terrain.glb",
    "roads":         "roads.glb",
    "buildings":     "buildings.glb",
    "vegetationData":"vegetation.json"
  },
  "roadGraph": "road-graph.json",
  "bounds": {
    "min": {"x": -500, "y": -50,  "z": -500},
    "max": {"x":  500, "y":  500, "z":  500}
  }
}
```

`bounds.y` range is hardcoded to −50 / +500 metres relative to `base_elevation`.

---

### Step 08 — Compress (`08_compress.py`)

**Input:** all `*.glb` files in `maps/<name>/`  
**Output:** compressed-in-place `.glb` files

Runs `gltfpack -cc` (maximum compression) on every GLB in the output directory. Files are overwritten in place. Step is silently skipped when `gltfpack` is not on `PATH`.

Install gltfpack: [https://github.com/zeux/meshoptimizer](https://github.com/zeux/meshoptimizer)

---

## Running the tests

```bash
cd /path/to/Brelly
pytest pipeline/tests/
```

Test modules:

| File | Coverage |
|------|----------|
| `test_coords.py` | LV95↔ENU conversion, bbox computation |
| `test_manifest.py` | manifest assembly from config |
| `test_road_graph.py` | node deduplication, edge construction |
| `test_e2e.py` | end-to-end pipeline run with a synthetic config |

---

## Troubleshooting

For installation issues (GDAL, Blender, pip errors) see [SETUP_MACOS.md](SETUP_MACOS.md) or [SETUP_WINDOWS.md](SETUP_WINDOWS.md).

| Symptom | Cause | Fix |
|---------|-------|-----|
| `WARNING: GDAL not available` | `gdal` Python bindings missing | macOS: SETUP_MACOS.md §3–4 · Windows: SETUP_WINDOWS.md §2–3 |
| `WARNING: Blender not found` | `blender` not on `PATH` | macOS: SETUP_MACOS.md §6 · Windows: SETUP_WINDOWS.md §5 |
| `WARNING: TLM source not found` | `source_data.tlm` path wrong | Check path in config JSON |
| `WARNING: gltfpack not found` | gltfpack not installed | Non-fatal — macOS: SETUP_MACOS.md §7 · Windows: SETUP_WINDOWS.md §6 |
| `FAILED: scripts/XX_*.py exited with code N` | Unhandled error in that step | Check stdout lines above for the specific error |
| `Road graph: 0 nodes, 0 edges` | Road layer missing from GeoPackage | Verify layer name is `tlm_strassen_strasse` |

---

## Data sources

- **swisstopo alti3D** — 0.5 m resolution digital elevation model covering Switzerland.  
  Download: https://www.swisstopo.admin.ch/en/height-model-swissalti3d

- **swissTLM3D** — topographic landscape model with roads, buildings, vegetation, and more.  
  Download: https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d

- **LV95 / EPSG:2056** — Swiss national coordinate system.  
  Reference: https://www.swisstopo.admin.ch/en/swiss-coordinate-system
