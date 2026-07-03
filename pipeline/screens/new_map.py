# pipeline/screens/new_map.py
"""New Map screen: takes a map name + DEM tiles (+ a remembered TLM path),
derives center/radius/base_elevation from the DEM, and writes
pipeline/config/<name>.json in the same schema the CLI already expects."""
from __future__ import annotations

import json
import re
import shutil
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from dem_config import derive_config_fields
from settings import load_settings, save_settings
from utils.dem import build_vrt

PROJECT_ROOT = Path(__file__).parent.parent.parent
PIPELINE_DIR = Path(__file__).parent.parent
CONFIG_DIR = PIPELINE_DIR / "config"
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_PATH = CONFIG_DIR / ".settings.json"

# data/ is where every map's downloaded source files live (see the DEM tiles
# folder and TLM GeoPackage fields below). It's gitignored — each machine
# builds up its own copy from swisstopo, nothing here is meant to be shared
# via the repo.
DEM_URL = "https://www.swisstopo.admin.ch/en/height-model-swissalti3d"
TLM_URL = "https://www.swisstopo.admin.ch/en/landscape-model-swisstlm3d"

_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def is_valid_map_name(name: str) -> bool:
    return bool(name) and bool(_NAME_RE.match(name))


def build_new_map_config(name: str, display_name: str, dem_path: str, tlm_path: str) -> dict:
    """Build the full config dict for a new map, deriving geospatial fields
    from the DEM and filling the rest with sensible defaults."""
    fields = derive_config_fields(dem_path)
    return {
        "name": name,
        "displayName": display_name or name,
        "center_e": fields["center_e"],
        "center_n": fields["center_n"],
        "radius_m": fields["radius_m"],
        "base_elevation": fields["base_elevation"],
        "terrain_cell_m": 1.0,
        "start_line": {
            "position": {"x": 0, "y": 0, "z": -50},
            "normal": {"x": 0, "y": 0, "z": 1},
            "widthMetres": 12,
        },
        "finish_line": {
            "position": {"x": 0, "y": 0, "z": 200},
            "normal": {"x": 0, "y": 0, "z": 1},
            "widthMetres": 12,
        },
        "spawn_position": {"x": 0, "y": 1, "z": -45},
        "spawn_rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
        "checkpoints": [],
        "source_data": {
            "dem": str(Path("data") / name / "alti3d.vrt"),
            "tlm": tlm_path,
        },
    }


try:
    import tkinter as tk
    from tkinter import ttk
    _TK_AVAILABLE = True
except ModuleNotFoundError:
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    _TK_AVAILABLE = False


class NewMapScreen(tk.Frame if _TK_AVAILABLE else object):  # type: ignore[misc]
    def __init__(self, parent, on_map_created=None) -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError("tkinter is not available in this Python environment.")
        super().__init__(parent)
        self._on_map_created = on_map_created
        self._dem_tiles_dir: Path | None = None
        self._settings = load_settings(SETTINGS_PATH)
        # Created eagerly (not just on map creation) so it exists as an
        # obvious drop target in Finder/Explorer before the user even opens
        # a file picker — it's gitignored, so nothing exists here on a
        # fresh checkout otherwise.
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._build_ui()

    def _build_ui(self) -> None:
        tk.Label(
            self,
            text="Downloaded files go under data/ (gitignored — each machine keeps its own copy).",
            fg="#94a3b8", font=("", 9),
        ).pack(anchor="w", padx=12, pady=(10, 0))

        form = tk.Frame(self)
        form.pack(fill="x", padx=12, pady=12)

        tk.Label(form, text="Map name:").grid(row=0, column=0, sticky="w", pady=4)
        self._name_var = tk.StringVar()
        tk.Entry(form, textvariable=self._name_var, width=26).grid(row=0, column=1, sticky="w")

        tk.Label(form, text="DEM tiles folder:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._dem_dir_var = tk.StringVar()
        tk.Entry(form, textvariable=self._dem_dir_var, width=32, state="readonly").grid(
            row=1, column=1, sticky="w", pady=(4, 0)
        )
        tk.Button(form, text="Browse…", command=self._pick_dem_dir).grid(row=1, column=2, padx=6, pady=(4, 0))
        dem_help = tk.Frame(form)
        dem_help.grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(
            dem_help, text="Elevation tiles (.tif) — swissALTI3D",
            fg="#94a3b8", font=("", 9),
        ).pack(side="left")
        tk.Button(
            dem_help, text="Open ↗", font=("", 9), command=lambda: webbrowser.open(DEM_URL),
        ).pack(side="left", padx=(6, 0))

        tk.Label(form, text="TLM GeoPackage:").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self._tlm_var = tk.StringVar(value=self._settings.get("tlm_path", ""))
        tk.Entry(form, textvariable=self._tlm_var, width=32).grid(row=3, column=1, sticky="w", pady=(4, 0))
        tk.Button(form, text="Browse…", command=self._pick_tlm_file).grid(row=3, column=2, padx=6, pady=(4, 0))
        tlm_help = tk.Frame(form)
        tlm_help.grid(row=4, column=1, columnspan=2, sticky="w", pady=(0, 4))
        tk.Label(
            tlm_help, text="Roads/buildings/vegetation (.gpkg) — swissTLM3D",
            fg="#94a3b8", font=("", 9),
        ).pack(side="left")
        tk.Button(
            tlm_help, text="Open ↗", font=("", 9), command=lambda: webbrowser.open(TLM_URL),
        ).pack(side="left", padx=(6, 0))

        self._status_var = tk.StringVar()
        tk.Label(self, textvariable=self._status_var, fg="#f44747").pack(anchor="w", padx=12)

        tk.Button(self, text="Create Map", command=self._on_create,
                  bg="#2d6a2d", activebackground="#3a8a3a").pack(anchor="w", padx=12, pady=8)

    def _pick_dem_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Select folder containing DEM .tif tiles", initialdir=str(DATA_DIR),
        )
        if chosen:
            self._dem_tiles_dir = Path(chosen)
            self._dem_dir_var.set(chosen)

    def _pick_tlm_file(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Select swissTLM3D GeoPackage", filetypes=[("GeoPackage", "*.gpkg")],
            initialdir=str(DATA_DIR),
        )
        if chosen:
            self._tlm_var.set(chosen)

    def _on_create(self) -> None:
        self._status_var.set("")
        name = self._name_var.get().strip()
        tlm_path = self._tlm_var.get().strip()

        if not is_valid_map_name(name):
            self._status_var.set("Map name must be non-empty and use only letters, numbers, - and _.")
            return
        if self._dem_tiles_dir is None:
            self._status_var.set("Select a folder containing DEM .tif tiles.")
            return
        if not tlm_path:
            self._status_var.set("Select a swissTLM3D GeoPackage.")
            return

        config_path = CONFIG_DIR / f"{name}.json"
        if config_path.exists():
            self._status_var.set(f"A config named '{name}' already exists.")
            return

        tif_files = sorted(str(p) for p in self._dem_tiles_dir.glob("*.tif"))
        if not tif_files:
            self._status_var.set("No .tif files found in that folder.")
            return

        map_data_dir = DATA_DIR / name
        vrt_path = map_data_dir / "alti3d.vrt"
        try:
            map_data_dir.mkdir(parents=True, exist_ok=True)
            vrt_built = build_vrt(tif_files, vrt_path)
        except OSError as exc:
            self._status_var.set(f"Failed to prepare DEM data folder: {exc}")
            return
        if not vrt_built:
            self._status_var.set("Failed to build VRT — is GDAL installed?")
            return

        try:
            config = build_new_map_config(name, name, str(vrt_path), tlm_path)
        except Exception as exc:
            shutil.rmtree(map_data_dir, ignore_errors=True)
            self._status_var.set(f"Failed to derive config from DEM: {exc}")
            return

        config_path.write_text(json.dumps(config, indent=2))

        save_settings(SETTINGS_PATH, {"tlm_path": tlm_path})

        messagebox.showinfo("Map created", f"Created {config_path.name}. Switching to Run screen.")
        if self._on_map_created:
            self._on_map_created(name)
