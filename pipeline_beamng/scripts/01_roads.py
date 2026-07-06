#!/usr/bin/env python3
# pipeline_beamng/scripts/01_roads.py
"""Convert the main pipeline's road_splines.json (smoothed, multi-point road
centerlines with per-node elevation) into BeamNG DecalRoad scene objects.

Deliberately reads road_splines.json, not road-graph.json: road-graph.json
collapses each road to its two endpoints (see pipeline/scripts/road_graph.py),
which would render curved roads as straight lines."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.io import read_json
from formats.coords import road_node_to_beamng
from formats.road import decalroad_object


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    name = config_dict["name"]

    splines_path = Path("maps") / name / "road_splines.json"
    if not splines_path.exists():
        raise FileNotFoundError(
            f"{splines_path} not found — run pipeline/run_pipeline.py for this "
            "map first; BeamNG road export reuses its smoothed road centerlines."
        )

    splines = read_json(splines_path)
    out_dir = Path("maps") / name / "beamng" / name
    out_dir.mkdir(parents=True, exist_ok=True)

    road_objects = []
    for road in splines:
        width = float(road["widthMetres"])
        nodes = []
        for pt in road["nodes"]:
            bx, by, bz = road_node_to_beamng(pt["x"], pt["y"], pt["z"])
            nodes.append([round(bx, 3), round(by, 3), round(bz, 3), round(width, 2)])
        if len(nodes) < 2:
            continue
        road_objects.append(decalroad_object(name=f"road_{road['id']}", nodes=nodes))

    (out_dir / "_road_objects.json").write_text(json.dumps(road_objects))
    print(f"BeamNG roads -> {len(road_objects)} DecalRoad objects")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
