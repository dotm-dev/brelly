#!/usr/bin/env python3
# pipeline/scripts/02_terrain.py
"""Generate terrain.glb from DEM via Blender."""
import sys, json, subprocess, shutil, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.io import read_json, ensure_dir, output_dir
from utils.coords import config_from_dict
from scripts._terrain_conform import conform_to_roads, RoadSegment


def write_placeholder_glb(path: Path) -> None:
    """Write the minimal valid binary GLB (empty scene) as a placeholder."""
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
    out_dir = ensure_dir(output_dir(config_dict))
    out_glb = out_dir / "terrain.glb"

    blender = shutil.which("blender")
    if not blender:
        print("WARNING: Blender not found. Writing placeholder terrain.glb.")
        write_placeholder_glb(out_glb)
        return

    data = _load_or_synthesize_heightmap(config_dict)
    data_json = out_dir / "_terrain_data.json"
    data_json.write_text(json.dumps(data))

    texture_path = _fetch_swissimage(config_dict, out_dir, tex_size=data["width"])

    baker = Path(__file__).parent.parent / "blender" / "terrain_baker.py"
    print(f"Baking terrain mesh in Blender ({data['width']}×{data['height']} grid)…", flush=True)
    baker_args = [str(data_json), str(out_glb)]
    if texture_path:
        baker_args.append(str(texture_path))
    result = subprocess.run(
        [blender, "--background", "--python", str(baker), "--", *baker_args],
        capture_output=True, text=True
    )
    data_json.unlink(missing_ok=True)
    # texture_path is intentionally kept on disk — acts as cache for future runs
    if result.returncode != 0:
        print(f"WARNING: Blender terrain bake failed. Writing placeholder.\n{result.stderr[-500:]}")
        write_placeholder_glb(out_glb)
    else:
        print(f"Terrain GLB → {out_glb}")


def _load_or_synthesize_heightmap(config_dict: dict) -> dict:
    """Try to load DEM via GDAL; fall back to a flat synthetic heightmap."""
    cell_size = 2.0
    fallback_size = 64
    try:
        from osgeo import gdal
        import numpy as np
        from utils.coords import bbox_from_center
        gdal.UseExceptions()
        config = config_from_dict(config_dict)
        dem_path = config_dict["source_data"].get("dem", "")
        if not Path(dem_path).exists():
            raise FileNotFoundError(dem_path)

        bbox = bbox_from_center(config)
        diameter = config.radius_m * 2
        n_cells = min(1024, max(64, int(diameter / cell_size)))
        actual_cell = diameter / n_cells

        ds = gdal.Open(dem_path)
        nodata = ds.GetRasterBand(1).GetNoDataValue()
        mem_ds = gdal.Warp(
            '', ds,
            format='MEM',
            outputBounds=(bbox['min_e'], bbox['min_n'], bbox['max_e'], bbox['max_n']),
            width=n_cells, height=n_cells,
            resampleAlg='bilinear',
            dstNodata=config.base_elevation,
        )
        arr = mem_ds.GetRasterBand(1).ReadAsArray().astype(float)
        arr -= config.base_elevation
        # GDAL row 0 = north; terrain_baker row 0 = south → flip
        arr = np.flipud(arr)

        # Road conforming — stamp road elevations into heightmap before meshing
        road_segments = _load_road_segments_for_conform(config_dict, bbox)
        if road_segments:
            conform_to_roads(
                arr, road_segments,
                min_e=bbox["min_e"], min_n=bbox["min_n"],
                cell_size=actual_cell, blend_cells=2,
            )
            print(f"  Road conforming: {len(road_segments)} segments applied", flush=True)

        return {"width": n_cells, "height": n_cells, "heights": arr.tolist(), "cell_size": actual_cell}
    except Exception as e:
        print(f"WARNING: Could not load DEM ({e}). Using flat heightmap.")
        heights = [[0.0] * fallback_size for _ in range(fallback_size)]
        return {"width": fallback_size, "height": fallback_size, "heights": heights, "cell_size": cell_size}


def _load_road_segments_for_conform(config_dict: dict, bbox: dict) -> list:
    """Load road centerlines from reprojected GPKG as RoadSegment objects."""
    try:
        from osgeo import ogr
        from utils.io import output_dir
        gpkg = output_dir(config_dict) / "reprojected.gpkg"
        if not gpkg.exists():
            return []
        ds = ogr.Open(str(gpkg))
        if ds is None:
            return []
        lyr = ds.GetLayerByName("tlm_strassen_strasse") or ds.GetLayer(0)
        if lyr is None:
            return []

        _WIDTHS = {
            "8m Strasse": 8.0, "6m Strasse": 6.0, "4m Strasse": 4.0,
            "3m Strasse": 3.0, "2m Weg": 2.0, "1m Weg": 1.5, "1m Wegfragment": 1.5,
        }

        segments = []
        defn = lyr.GetLayerDefn()
        obj_idx = defn.GetFieldIndex("OBJEKTART")  # -1 if field absent
        lyr.SetSpatialFilterRect(bbox["min_e"], bbox["min_n"], bbox["max_e"], bbox["max_n"])

        for feat in lyr:
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            raw = feat.GetField(obj_idx) if obj_idx >= 0 else None
            width = _WIDTHS.get(raw, 4.0)
            pts = [
                (geom.GetX(i), geom.GetY(i), geom.GetZ(i) if geom.Is3D() else 0.0)
                for i in range(geom.GetPointCount())
            ]
            if len(pts) >= 2:
                segments.append(RoadSegment(points=pts, half_width=width / 2))
        return segments
    except Exception as e:
        print(f"  WARNING: road conforming skipped ({e})", flush=True)
        return []


def _fetch_swissimage(config_dict: dict, out_dir: Path, tex_size: int = 1024) -> str | None:
    """Download SWISSIMAGE orthophoto for the map bbox via swisstopo WMTS. Returns path or None."""
    try:
        from utils.coords import config_from_dict
        config = config_from_dict(config_dict)
    except Exception:
        return None

    # Cache key includes radius so a changed extent triggers a re-fetch.
    out_path = out_dir / f"_terrain_texture_{config.radius_m:.0f}.jpg"
    if out_path.exists():
        print(f"SWISSIMAGE texture cached → {out_path}")
        return str(out_path)

    try:
        from osgeo import gdal
        from utils.coords import bbox_from_center
        gdal.UseExceptions()

        bbox = bbox_from_center(config)  # LV95 (EPSG:2056)

        # GDAL WMS descriptor — swisstopo SWISSIMAGE WMTS in Web Mercator
        wms_xml = (
            "<GDAL_WMS><Service name=\"TMS\">"
            "<ServerUrl>https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage"
            "/default/current/3857/${z}/${x}/${y}.jpeg</ServerUrl>"
            "</Service>"
            "<DataWindow>"
            "<UpperLeftX>-20037508.34</UpperLeftX><UpperLeftY>20037508.34</UpperLeftY>"
            "<LowerRightX>20037508.34</LowerRightX><LowerRightY>-20037508.34</LowerRightY>"
            "<TileLevel>17</TileLevel>"
            "<TileCountX>1</TileCountX><TileCountY>1</TileCountY>"
            "<YOrigin>top</YOrigin>"
            "</DataWindow>"
            "<Projection>EPSG:3857</Projection>"
            "<BlockSizeX>256</BlockSizeX><BlockSizeY>256</BlockSizeY>"
            "<BandsCount>3</BandsCount>"
            "<Cache/>"
            "</GDAL_WMS>"
        )

        print("Fetching SWISSIMAGE orthophoto…", flush=True)
        wms_ds = gdal.Open(wms_xml)
        if wms_ds is None:
            raise RuntimeError("Could not open WMTS source")

        mem_ds = gdal.Warp(
            "",
            wms_ds,
            format="MEM",
            outputBounds=(bbox["min_e"], bbox["min_n"], bbox["max_e"], bbox["max_n"]),
            outputBoundsSRS="EPSG:2056",
            dstSRS="EPSG:2056",
            width=tex_size,
            height=tex_size,
            resampleAlg="bilinear",
        )
        if mem_ds is None:
            raise RuntimeError("Warp returned empty dataset")

        # Write directly — no flipud. GDAL row 0 = north = image top.
        # Blender loads JPEGs with row 0 at v=1 (top), matching our UV where
        # v=1 = north. The glTF exporter then flips V (bottom-left → top-left
        # origin), which keeps north at the correct end for Babylon.js.
        gdal.GetDriverByName("JPEG").CreateCopy(str(out_path), mem_ds, options=["QUALITY=90"])
        mem_ds = None
        print(f"SWISSIMAGE texture → {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"WARNING: Could not fetch SWISSIMAGE ({e}). Terrain will be untextured.")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
