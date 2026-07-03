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
from dem_config import derive_config_fields, derive_config_fields_from_csv
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


def build_new_map_config(name: str, display_name: str, tlm_path: str, fields: dict) -> dict:
    """Build the full config dict for a new map from already-derived
    geospatial fields (see dem_config.derive_config_fields /
    derive_config_fields_from_csv) and sensible defaults for the rest."""
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
        self._dem_csv_path: Path | None = None
        self._settings = load_settings(SETTINGS_PATH)
        # Created eagerly (not just on map creation) so it exists as an
        # obvious drop target in Finder/Explorer before the user even opens
        # a file picker — it's gitignored, so nothing exists here on a
        # fresh checkout otherwise.
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._build_ui()

    def _link(self, parent, text: str, url: str) -> "tk.Label":
        """Small hyperlink-style label — subtler than a full tk.Button."""
        label = tk.Label(parent, text=text, fg="#4a9eda", cursor="hand2", font=("", 9, "underline"))
        label.bind("<Button-1>", lambda _e: webbrowser.open(url))
        return label

    def _bullet(self, parent, row: int, prefix: str, path: str, link_text: str, url: str) -> None:
        """One intro line: prose, a monospace-bold folder path, then a
        hyperlink — all inline so the path reads as a literal path rather
        than blending into the sentence."""
        line = tk.Frame(parent)
        line.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        tk.Label(line, text=f"•  {prefix}", font=("", 9), fg="#94a3b8").pack(side="left")
        tk.Label(line, text=path, font=("Courier", 9, "bold"), fg="#c9d1e0").pack(side="left")
        self._link(line, link_text, url).pack(side="left", padx=(6, 0))

    def _default_tlm_path(self) -> str:
        """Remembered TLM path if any, else auto-detect a .gpkg sitting
        directly in data/ (the download-once-share-everywhere convention)."""
        remembered = self._settings.get("tlm_path", "")
        if remembered and Path(remembered).exists():
            return remembered
        found = sorted(DATA_DIR.glob("*.gpkg"))
        return str(found[0]) if found else ""

    def _build_ui(self) -> None:
        intro = tk.Frame(self)
        intro.pack(fill="x", padx=12, pady=(12, 4))

        tk.Label(
            intro, text="A map is built from two free swisstopo datasets:", font=("", 10),
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        self._bullet(
            intro, row=1,
            prefix="Elevation tiles (.tif) for your area — place them in ",
            path="data/<map name>/",
            link_text="swissALTI3D ↗", url=DEM_URL,
        )
        self._bullet(
            intro, row=2,
            prefix="Landscape file (.gpkg), one download for all maps — place it in ",
            path="data/",
            link_text="swissTLM3D ↗", url=TLM_URL,
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=(8, 4))

        form = tk.Frame(self)
        form.pack(fill="x", padx=12, pady=8)

        tk.Label(form, text="Map name:").grid(row=0, column=0, sticky="w", pady=4)
        self._name_var = tk.StringVar()
        tk.Entry(form, textvariable=self._name_var, width=26).grid(row=0, column=1, sticky="w")

        tk.Label(form, text="Elevation tiles:").grid(row=1, column=0, sticky="w", pady=(17, 4))
        mode_row = tk.Frame(form)
        mode_row.grid(row=1, column=1, columnspan=2, sticky="w", pady=(17, 0))
        self._dem_mode = tk.StringVar(value="folder")
        tk.Radiobutton(
            mode_row, text="I already downloaded the tiles", variable=self._dem_mode,
            value="folder", command=self._on_dem_mode_change,
        ).pack(side="left")
        tk.Radiobutton(
            mode_row, text="I have a swisstopo download-links CSV", variable=self._dem_mode,
            value="csv", command=self._on_dem_mode_change,
        ).pack(side="left", padx=(10, 0))

        self._dem_source_label_var = tk.StringVar(value="Tiles folder:")
        tk.Label(form, textvariable=self._dem_source_label_var).grid(row=2, column=0, sticky="w", pady=4)
        self._dem_dir_var = tk.StringVar()
        tk.Entry(form, textvariable=self._dem_dir_var, width=32, state="readonly").grid(row=2, column=1, sticky="w")
        tk.Button(form, text="Browse…", command=self._pick_dem_source).grid(row=2, column=2, padx=6)
        self._dem_hint_var = tk.StringVar(
            value="Pick the folder you already downloaded swissALTI3D .tif tiles into."
        )
        tk.Label(
            form, textvariable=self._dem_hint_var, fg="#94a3b8", font=("", 9),
            wraplength=420, justify="left",
        ).grid(row=3, column=1, columnspan=2, sticky="w", pady=(0, 13))

        tk.Label(form, text="Landscape file:").grid(row=4, column=0, sticky="w", pady=4)
        self._tlm_var = tk.StringVar(value=self._default_tlm_path())
        tk.Entry(form, textvariable=self._tlm_var, width=32).grid(row=4, column=1, sticky="w")
        tk.Button(form, text="Browse…", command=self._pick_tlm_file).grid(row=4, column=2, padx=6)

        self._status_var = tk.StringVar()
        tk.Label(self, textvariable=self._status_var, fg="#f44747", wraplength=560, justify="left").pack(
            anchor="w", padx=12
        )

        tk.Button(self, text="Create Map", command=self._on_create,
                  bg="#2d6a2d", activebackground="#3a8a3a").pack(anchor="w", padx=12, pady=8)

    def _on_dem_mode_change(self) -> None:
        self._dem_tiles_dir = None
        self._dem_csv_path = None
        self._dem_dir_var.set("")
        if self._dem_mode.get() == "csv":
            self._dem_source_label_var.set("CSV file:")
            self._dem_hint_var.set(
                "Pick the ch.swisstopo....csv swisstopo gives you when too many tiles are "
                "selected. Tiles download automatically the first time you run the pipeline."
            )
        else:
            self._dem_source_label_var.set("Tiles folder:")
            self._dem_hint_var.set("Pick the folder you already downloaded swissALTI3D .tif tiles into.")

    def _pick_dem_source(self) -> None:
        if self._dem_mode.get() == "csv":
            chosen = filedialog.askopenfilename(
                title="Select swisstopo download-links CSV", filetypes=[("CSV", "*.csv")],
                initialdir=str(DATA_DIR),
            )
            if chosen:
                self._dem_csv_path = Path(chosen)
                self._dem_tiles_dir = None
                self._dem_dir_var.set(chosen)
        else:
            chosen = filedialog.askdirectory(
                title="Select folder containing DEM .tif tiles", initialdir=str(DATA_DIR),
            )
            if chosen:
                self._dem_tiles_dir = Path(chosen)
                self._dem_csv_path = None
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
        mode = self._dem_mode.get()

        if not is_valid_map_name(name):
            self._status_var.set("Map name must be non-empty and use only letters, numbers, - and _.")
            return
        if mode == "folder" and self._dem_tiles_dir is None:
            self._status_var.set("Select a folder containing DEM .tif tiles.")
            return
        if mode == "csv" and self._dem_csv_path is None:
            self._status_var.set("Select a swisstopo download-links CSV.")
            return
        if not tlm_path:
            self._status_var.set("Select a swissTLM3D GeoPackage.")
            return

        config_path = CONFIG_DIR / f"{name}.json"
        if config_path.exists():
            self._status_var.set(f"A config named '{name}' already exists.")
            return

        map_data_dir = DATA_DIR / name
        # Only clean up map_data_dir on failure if we're the ones who
        # created it — on a case-insensitive filesystem (default on macOS),
        # "Test" and "test" resolve to the same directory, so a name that
        # collides case-insensitively with an existing folder must never
        # have its pre-existing contents wiped out by our own error path.
        already_existed = map_data_dir.exists()
        try:
            map_data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._status_var.set(f"Failed to prepare DEM data folder: {exc}")
            return

        if mode == "folder":
            fields = self._create_from_tiles_folder(map_data_dir, cleanup=not already_existed)
        else:
            fields = self._create_from_csv(map_data_dir, cleanup=not already_existed)
        if fields is None:
            return  # error already shown, map_data_dir cleaned up if it was safe to

        config = build_new_map_config(name, name, tlm_path, fields)
        config_path.write_text(json.dumps(config, indent=2))

        save_settings(SETTINGS_PATH, {"tlm_path": tlm_path})

        if mode == "csv":
            messagebox.showinfo(
                "Map created",
                f"Created {config_path.name}. Tiles will download automatically the "
                "first time you run the pipeline for this map. Switching to Run screen.",
            )
        else:
            messagebox.showinfo("Map created", f"Created {config_path.name}. Switching to Run screen.")
        if self._on_map_created:
            self._on_map_created(name)

    def _fail(self, message: str, map_data_dir: Path, cleanup: bool) -> None:
        self._status_var.set(message)
        if cleanup:
            shutil.rmtree(map_data_dir, ignore_errors=True)

    def _create_from_tiles_folder(self, map_data_dir: Path, cleanup: bool) -> dict | None:
        """Build the VRT from already-downloaded tiles and derive exact
        fields from it. Returns None (after cleaning up, if safe to) on
        failure."""
        tif_files = sorted(str(p) for p in self._dem_tiles_dir.glob("*.tif"))
        if not tif_files:
            self._fail("No .tif files found in that folder.", map_data_dir, cleanup)
            return None

        vrt_path = map_data_dir / "alti3d.vrt"
        try:
            vrt_built = build_vrt(tif_files, vrt_path)
        except OSError as exc:
            self._fail(f"Failed to build VRT: {exc}", map_data_dir, cleanup)
            return None
        if not vrt_built:
            self._fail("Failed to build VRT — is GDAL installed?", map_data_dir, cleanup)
            return None

        try:
            return derive_config_fields(str(vrt_path))
        except Exception as exc:
            self._fail(f"Failed to derive config from DEM: {exc}", map_data_dir, cleanup)
            return None

    def _create_from_csv(self, map_data_dir: Path, cleanup: bool) -> dict | None:
        """Copy the CSV into data/<name>/ (so the pipeline's download step
        finds it) and derive approximate fields from tile filenames alone —
        no download needed yet. base_elevation is a 0.0 placeholder, self-
        corrected by 00_download.py once real tiles land."""
        try:
            fields = derive_config_fields_from_csv(str(self._dem_csv_path))
        except Exception as exc:
            self._fail(f"Failed to read tile grid from CSV: {exc}", map_data_dir, cleanup)
            return None

        # Always land under a name matching what 00_download.py's glob
        # expects (ch.swisstopo.*.csv), regardless of what the browser
        # actually saved it as. Safari in particular renders swisstopo's
        # CSV inline instead of downloading it, so "Save As" names the file
        # after the page (e.g. "tif.csv"), not swisstopo's own filename —
        # the CSV's *content* (real tile coordinates, checked above) is
        # what actually matters, not what it happened to be called.
        dest = map_data_dir / f"ch.swisstopo.swissalti3d-{map_data_dir.name}.csv"
        # The CSV may already sit exactly where we'd copy it — e.g. the map
        # name collides case-insensitively with an existing data/ folder
        # (macOS's default filesystem), or the user just points at a file
        # already placed correctly. Copying a file onto itself is an error,
        # not a real failure, so skip it rather than reporting one.
        try:
            already_in_place = self._dem_csv_path.samefile(dest)
        except OSError:
            already_in_place = False
        if not already_in_place:
            try:
                shutil.copy2(self._dem_csv_path, dest)
            except OSError as exc:
                self._fail(f"Failed to copy CSV into data folder: {exc}", map_data_dir, cleanup)
                return None

        return fields
