#!/usr/bin/env python3
# pipeline/scripts/00_download.py
"""Download missing SwissALTI3D tiles listed in swisstopo CSV files.

Swisstopo generates a CSV of download URLs when too many tiles are selected in
the map viewer. Place the CSV next to the DEM tiles (same directory as the VRT).
This script reads every ch.swisstopo.*.csv in that directory, checks which
.tif files are already present, and downloads the rest.
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.io import read_json


def main(config_path: str) -> None:
    config = read_json(config_path)
    dem_vrt = Path(config["source_data"]["dem"])
    data_dir = dem_vrt.parent

    csv_files = sorted(data_dir.glob("ch.swisstopo.*.csv"))
    if not csv_files:
        print("No swisstopo CSV files found — skipping download step.")
        return

    urls: list[str] = []
    for csv_path in csv_files:
        for line in csv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                urls.append(line)

    if not urls:
        print("CSV files are empty — nothing to download.")
        return

    missing = [u for u in urls if not (data_dir / Path(u).name).exists()]

    if not missing:
        print(f"All {len(urls)} tiles already present — nothing to download.")
        return

    print(f"Downloading {len(missing)} / {len(urls)} missing tiles into {data_dir}/")
    for i, url in enumerate(missing, 1):
        dest = data_dir / Path(url).name
        print(f"  [{i}/{len(missing)}] {dest.name}", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as exc:
            print(f"  ERROR downloading {url}: {exc}", file=sys.stderr)

    print("Download complete.")
    _rebuild_vrt(dem_vrt, data_dir)


def _rebuild_vrt(vrt_path: Path, data_dir: Path) -> None:
    """Rebuild the VRT index from all .tif files in data_dir."""
    from utils.dem import build_vrt

    tif_files = sorted(str(p) for p in data_dir.glob("*.tif"))
    if not tif_files:
        print("No .tif files found — skipping VRT rebuild.")
        return

    print(f"Rebuilding VRT from {len(tif_files)} tiles → {vrt_path.name}", flush=True)
    if build_vrt(tif_files, vrt_path):
        print("VRT rebuilt.")
    else:
        print("ERROR: VRT rebuild failed (GDAL unavailable or build failed).", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {__file__} <config.json>")
        sys.exit(1)
    main(sys.argv[1])
