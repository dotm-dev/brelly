#!/usr/bin/env python3
# pipeline/scripts/03_roads.py
"""Generate roads.glb from TLM road vectors via Blender."""
import re
import sys, json, subprocess, shutil, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.io import read_json, ensure_dir, output_dir, progress
from utils.coords import config_from_dict, lv95_to_enu
from scripts.road_graph import build_road_graph, RoadLine


def write_placeholder_glb(path: Path) -> None:
    json_content = b'{"asset":{"version":"2.0"}}'
    padding = (4 - len(json_content) % 4) % 4
    json_content += b' ' * padding
    chunk0 = struct.pack('<II', len(json_content), 0x4E4F534A) + json_content
    total = 12 + len(chunk0)
    header = struct.pack('<III', 0x46546C67, 2, total)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + chunk0)


def main(config_path: str) -> None:
    config_dict = read_json(config_path)
    config = config_from_dict(config_dict)
    out_dir = ensure_dir(output_dir(config_dict))
    out_glb = out_dir / "roads.glb"

    blender = shutil.which("blender")
    if not blender:
        print("WARNING: Blender not found. Writing placeholder roads.glb.")
        write_placeholder_glb(out_glb)
        return

    roads = _load_roads(out_dir / "reprojected.gpkg")
    if not roads:
        print("WARNING: No road data found. Writing placeholder roads.glb.")
        write_placeholder_glb(out_glb)
        return
    roads_data = []
    for road in roads:
        coords_enu = [list(lv95_to_enu(e, n, elev, config)) for e, n, elev in road.coords_lv95]
        roads_data.append({"coords": coords_enu, "width": road.width_m, "road_type": road.road_type})

    roads_json = out_dir / "_roads_data.json"
    roads_json.write_text(json.dumps(roads_data))
    baker = Path(__file__).parent.parent / "blender" / "road_baker.py"
    print(f"Baking {len(roads_data)} road segments in Blender…", flush=True)
    try:
        result = subprocess.run(
            [blender, "--background", "--python", str(baker),
             "--", str(roads_json), str(out_glb)],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("WARNING: Blender timed out after 300s. Writing placeholder roads.glb.")
        roads_json.unlink(missing_ok=True)
        write_placeholder_glb(out_glb)
        return
    roads_json.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"WARNING: Blender road bake failed.\n{result.stderr[-500:]}")
        write_placeholder_glb(out_glb)
    else:
        print(f"Roads GLB → {out_glb}")


_OBJEKTART_MAP = {
    "Autobahn":       ("road_major", 14.0),
    "Autostrasse":    ("road_major", 12.0),
    "10m Strasse":    ("road_major", 10.0),
    "8m Strasse":     ("road_major",  8.0),
    "6m Strasse":     ("road_main",   6.0),
    "4m Strasse":     ("road_local",  4.0),
    "3m Strasse":     ("road_small",  3.0),
    "Verbindung":     ("road_local",  4.0),
    "Einfahrt":       ("road_small",  3.0),
    "Ausfahrt":       ("road_small",  3.0),
    "Zufahrt":        ("road_small",  3.0),
    "Dienstzufahrt":  ("road_small",  2.5),
    "Raststaette":    ("road_local",  4.0),
    "2m Weg":         ("path",        2.0),
    "2m Wegfragment": ("path",        2.0),
    "1m Weg":         ("path",        1.5),
    "1m Wegfragment": ("path",        1.5),
    "Markierte Spur": ("path",        1.5),
    # Non-road features — skip
    "Platz":          None,
    "Klettersteig":   None,
    "Faehre":         None,
    "Autozug":        None,
}

def _parse_objektart(raw: str) -> tuple[str, float] | None:
    """Return (road_type, width_m) or None to skip this feature."""
    if raw and raw in _OBJEKTART_MAP:
        return _OBJEKTART_MAP[raw]
    # fallback: try to extract width from "Xm ..." pattern
    m = re.match(r"(\d+(?:\.\d+)?)m", raw or "")
    width = float(m.group(1)) if m else 4.0
    road_type = "path" if "Weg" in (raw or "") else "road_local"
    return road_type, width


def _load_roads(gpkg_path: Path) -> list[RoadLine]:
    try:
        from osgeo import ogr
        ds = ogr.Open(str(gpkg_path))
        if ds is None:
            return []
        lyr = ds.GetLayerByName("tlm_strassen_strasse") or ds.GetLayer(0)
        if lyr is None:
            return []
        roads = []
        total = lyr.GetFeatureCount()
        obj_idx = -1
        for j, feat in enumerate(lyr, 1):
            if j == 1:
                obj_idx = feat.GetFieldIndex("OBJEKTART")
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            raw_obj = feat.GetField(obj_idx) if obj_idx >= 0 else None
            parsed = _parse_objektart(raw_obj)
            if parsed is None:
                continue
            road_type, width_m = parsed
            coords = [(geom.GetX(i), geom.GetY(i), geom.GetZ(i) if geom.Is3D() else 0.0)
                      for i in range(geom.GetPointCount())]
            roads.append(RoadLine(id=str(feat.GetFID()), coords_lv95=coords, width_m=width_m, road_type=road_type))
            if total > 0 and (j % max(1, total // 20) == 0 or j == total):
                progress("loading roads", j, total)
        return roads
    except Exception:
        return []


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
