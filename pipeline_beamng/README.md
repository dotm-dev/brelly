# BeamNG Export Pipeline

Exports a Brelly map as a BeamNG.drive level (terrain + roads). Runs after
the main [`pipeline/`](../pipeline/README.md) — it reuses that pipeline's
config and intermediate outputs rather than reprocessing source geodata.

## Prerequisites

Run the main pipeline for the map first:

```bash
python pipeline/run_pipeline.py pipeline/config/<my_map>.json
```

This produces `maps/<my_map>/road_splines.json`, which the roads step below
requires.

## Running the pipeline

```bash
cd /path/to/Brelly
source .venv/bin/activate
python pipeline_beamng/run_beamng_pipeline.py pipeline/config/<my_map>.json
```

Output lands in `maps/<my_map>/beamng/<my_map>/` as a BeamNG level folder
(`info.json`, `main/MissionGroup/...`, terrain `.ter`/`.terrain.json`/PNG).
Copy that folder into your BeamNG.drive `levels/` directory to play it.

To run a single step in isolation:

```bash
python pipeline_beamng/scripts/00_terrain.py pipeline/config/<my_map>.json
```

## Pipeline steps

### Step 00 — Terrain (`scripts/00_terrain.py`)

Reads the map's DEM directly via GDAL (independent of `pipeline/`'s
`terrain.glb`, which never caches a raw heightmap grid). Warps it to a
power-of-two grid (512–4096, targeting ~2 m/pixel), encodes it as a 16-bit
BeamNG heightmap, and writes `<name>.ter`, `<name>_heightmap.png`, and
`<name>.terrain.json`.

### Step 01 — Roads (`scripts/01_roads.py`)

Reads `maps/<name>/road_splines.json` — the main pipeline's smoothed,
multi-point road centerlines (deliberately *not* `road-graph.json`, which
collapses each road to two endpoints and would render curves as straight
lines). Converts each node to BeamNG's coordinate frame and writes DecalRoad
scene objects.

### Step 02 — Package (`scripts/02_package.py`)

Assembles the level folder: nests the terrain and road scene objects into
the `main/MissionGroup/level_object/terrain` SimGroup hierarchy real BeamNG
levels use, adds a default spawn point derived from the config's
`spawn_position`, and writes `info.json` with level metadata.

## Layout

```
pipeline_beamng/
├── run_beamng_pipeline.py   # orchestrator (subprocess-per-step, mirrors pipeline/)
├── scripts/                 # 00_terrain.py, 01_roads.py, 02_package.py
├── formats/                 # coords.py, terrain.py, road.py — BeamNG file writers
└── tests/                   # pytest suite
```

Shared helpers (DEM/coords/JSON I/O) live in the top-level
[`shared/utils/`](../shared/utils/), used by both this pipeline and
`pipeline/`.

## Running the tests

```bash
cd /path/to/Brelly
pytest pipeline_beamng/tests/
```

## Known gaps

- Only terrain and roads are exported — no buildings or vegetation yet.
- Terrain north/south orientation relative to BeamNG's world axes is
  unverified in-game (see comment in `scripts/00_terrain.py`).
