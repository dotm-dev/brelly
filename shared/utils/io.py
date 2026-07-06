# pipeline/utils/io.py
import sys
import warnings
import json
from pathlib import Path

# suppress the GDAL "UseExceptions not called" FutureWarning that appears on every import
warnings.filterwarnings("ignore", category=FutureWarning, module="osgeo")


def progress(label: str, current: int, total: int) -> None:
    """Print an in-place progress line: 'label  42%  (420/1000)'"""
    if total <= 0:
        return
    pct = int(current / total * 100)
    line = f"  {label}  {pct:3d}%  ({current}/{total})"
    if sys.stdout.isatty():
        print(f"\r{line}", end="", flush=True)
        if current >= total:
            print()
    else:
        # when piped to a file only print at 0%, 25%, 50%, 75%, 100%
        milestones = {0, 25, 50, 75, 100}
        if pct in milestones or current == total:
            print(line, flush=True)


def read_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_dir(config: dict) -> Path:
    return Path("maps") / config["name"]
