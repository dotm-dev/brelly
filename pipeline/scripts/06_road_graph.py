#!/usr/bin/env python3
# pipeline/scripts/06_road_graph.py
"""Extract road centerlines from reprojected data and build road-graph.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))                # repo root, for shared/
from shared.utils.io import read_json, write_json, output_dir, progress
from shared.utils.coords import config_from_dict
from scripts.road_graph import RoadLine, build_road_graph


def _parse_width(objektart: object) -> float:
    """Extract a numeric width from OBJEKTART strings like '6m Strasse' or '3m Weg'."""
    import re
    if objektart is None:
        return 6.0
    m = re.search(r'(\d+(?:\.\d+)?)', str(objektart))
    return float(m.group(1)) if m else 6.0


def load_roads_from_gpkg(gpkg_path: str, layer: str = "tlm_strassen_strasse") -> list[RoadLine]:
    """Load road centerlines from a reprojected GeoPackage."""
    try:
        from osgeo import ogr
    except ImportError:
        print("WARNING: GDAL not available. Returning empty road list.")
        return []

    ds = ogr.Open(gpkg_path)
    if ds is None:
        print(f"WARNING: Could not open {gpkg_path}. Returning empty road list.")
        return []

    lyr = ds.GetLayerByName(layer)
    if lyr is None:
        lyr = ds.GetLayer(0)
    if lyr is None:
        return []

    roads = []
    total = lyr.GetFeatureCount()
    for j, feat in enumerate(lyr, 1):
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        coords = []
        for i in range(geom.GetPointCount()):
            coords.append((geom.GetX(i), geom.GetY(i), geom.GetZ(i) if geom.Is3D() else 0.0))
        width = _parse_width(feat.GetField("OBJEKTART")) if feat.GetFieldIndex("OBJEKTART") >= 0 else 6.0
        roads.append(RoadLine(id=str(feat.GetFID()), coords_lv95=coords, width_m=width))
        if total > 0 and (j % max(1, total // 20) == 0 or j == total):
            progress("processing roads", j, total)
    return roads


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    config = config_from_dict(config_dict)
    out_dir = output_dir(config_dict)

    gpkg_path = str(out_dir / "reprojected.gpkg")
    roads = load_roads_from_gpkg(gpkg_path)
    graph = build_road_graph(roads, config)

    out_path = out_dir / "road-graph.json"
    write_json(out_path, graph)
    print(f"Road graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
