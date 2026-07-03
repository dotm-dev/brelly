# pipeline/screens/run.py
"""Run screen: pick a map config, choose which steps to run, watch the log.
This is the GUI surface for run_pipeline.py. Also owns the "+ New Map"
popup, since creating a map only matters in the context of picking one to
run — there's no need for it to be a persistent tab."""
from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from run_pipeline import SCRIPTS
from system_checks import map_data_ready
from screens.new_map import NewMapScreen
from screens.ui import center_window

PROJECT_ROOT = Path(__file__).parent.parent.parent
PIPELINE_DIR = Path(__file__).parent.parent
CONFIG_DIR = PIPELINE_DIR / "config"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"


def step_labels() -> list[str]:
    """Step labels in pipeline order, derived from run_pipeline.SCRIPTS so
    this list can never drift out of sync with the orchestrator."""
    return [label for label, _script in SCRIPTS]


def scan_configs(config_dir: Path) -> list[tuple[str, Path]]:
    """Return [(display_name, path), ...] sorted by display name, excluding
    example.json and dotfiles (e.g. .settings.json)."""
    results = []
    for p in sorted(config_dir.glob("*.json")):
        if p.stem == "example" or p.name.startswith("."):
            continue
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
        name = data.get("name") or p.stem
        results.append((name, p))
    return results


def build_run_config(source: Path, skip: set[str], dest: Path) -> None:
    """Write a copy of source config with skip_steps replaced by skip."""
    data = json.loads(source.read_text())
    data["skip_steps"] = sorted(skip)
    dest.write_text(json.dumps(data, indent=2))


def run_subprocess(cmd: list[str], out_queue: "queue.Queue[str | None]") -> None:
    """Run cmd in a background thread, put each output line into out_queue.
    Puts None when done."""
    def _target() -> None:
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=str(PROJECT_ROOT),
            )
            if proc.stdout is None:
                raise RuntimeError("Popen stdout is None — unexpected")
            for line in proc.stdout:
                out_queue.put(line.rstrip("\n"))
            proc.wait()
            if proc.returncode != 0:
                out_queue.put(f"✗ process exited with code {proc.returncode}")
            out_queue.put(None)
        except Exception as exc:
            out_queue.put(f"ERROR: {exc}")
            out_queue.put(None)

    t = threading.Thread(target=_target, daemon=True)
    t.start()


try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
    _TK_AVAILABLE = True
except ModuleNotFoundError:
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    scrolledtext = None  # type: ignore[assignment]
    _TK_AVAILABLE = False


class RunScreen(tk.Frame if _TK_AVAILABLE else object):  # type: ignore[misc]
    """Map list (with per-map data-readiness status), step-skip checkboxes,
    log pane. A tk.Frame meant to be embedded inside the top-level App (see
    app.py), not a standalone window."""

    def __init__(self, parent) -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError("tkinter is not available in this Python environment.")
        super().__init__(parent)

        self._configs: list[tuple[str, Path]] = []
        self._ready: dict[str, bool] = {}
        self._skip: dict[str, tk.BooleanVar] = {}
        self._running = False
        self._log_queue: queue.Queue[str | None] = queue.Queue()
        self._tmp_config: Path | None = None
        self._new_map_popup: tk.Toplevel | None = None

        self._build_ui()
        self.refresh_configs()

    def refresh_configs(self) -> None:
        """Re-scan pipeline/config/ and re-check each map's data readiness."""
        self._configs = scan_configs(CONFIG_DIR)
        self._populate_tree()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 6}

        top = tk.Frame(self)
        top.pack(fill="x", **pad)
        tk.Label(top, text="Maps", font=("", 12, "bold")).pack(side="left")
        tk.Button(top, text="Refresh", command=self.refresh_configs).pack(side="right")
        tk.Button(top, text="+ New Map", command=self._open_new_map_popup).pack(side="right", padx=(0, 6))

        self._tree = ttk.Treeview(
            self, columns=("status",), show="tree headings", selectmode="browse", height=6,
        )
        self._tree.heading("#0", text="Map")
        self._tree.heading("status", text="Status")
        self._tree.column("#0", width=220)
        self._tree.column("status", width=200)
        self._tree.tag_configure("ready", foreground="#6a9955")
        self._tree.tag_configure("not_ready", foreground="#f44747")
        self._tree.pack(fill="x", padx=8)
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._on_tree_select())

        self._empty_label = tk.Label(
            self, text="No maps yet — click + New Map to create one.", fg="#94a3b8",
        )

        self._btn_run = tk.Button(
            self, text="Run Pipeline", command=self._on_run_pipeline,
            width=14, bg="#2d6a2d", activebackground="#3a8a3a",
        )
        self._btn_run.pack(anchor="w", padx=8, pady=(6, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=(6, 0))

        steps_frame = tk.LabelFrame(self, text="Steps", padx=8, pady=4)
        steps_frame.pack(fill="x", padx=8, pady=(4, 2))

        for i, step in enumerate(step_labels()):
            var = tk.BooleanVar(value=True)
            self._skip[step] = var
            cb = tk.Checkbutton(steps_frame, text=step, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=6, pady=2)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=(4, 0))

        self._log = scrolledtext.ScrolledText(
            self, font=("Courier", 11), wrap="word", state="disabled",
            bg="#1e1e1e", fg="#d4d4d4",
        )
        self._log.pack(fill="both", expand=True, padx=8, pady=6)
        self._log.tag_config("error", foreground="#f44747")
        self._log.tag_config("ok", foreground="#6a9955")

    def _populate_tree(self) -> None:
        selected = self._selected_name()
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._ready = {}

        if not self._configs:
            self._empty_label.pack(anchor="w", padx=8, pady=(0, 6))
        else:
            self._empty_label.pack_forget()

        first_ready = None
        for name, path in self._configs:
            result = map_data_ready(path, PROJECT_ROOT)
            self._ready[name] = result.ok
            status = "✓ ready" if result.ok else f"✗ {result.detail}"
            tag = "ready" if result.ok else "not_ready"
            self._tree.insert("", "end", iid=name, text=name, values=(status,), tags=(tag,))
            if result.ok and first_ready is None:
                first_ready = name

        to_select = selected if selected in self._ready else first_ready
        if to_select is not None:
            self._tree.selection_set(to_select)
            self._tree.see(to_select)
        self._on_tree_select()

    def _selected_name(self) -> str | None:
        selection = self._tree.selection() if hasattr(self, "_tree") else ()
        return selection[0] if selection else None

    def _on_tree_select(self) -> None:
        name = self._selected_name()
        can_run = name is not None and self._ready.get(name, False) and not self._running
        self._btn_run.config(state="normal" if can_run else "disabled")

    def _open_new_map_popup(self) -> None:
        if self._new_map_popup is not None and self._new_map_popup.winfo_exists():
            self._new_map_popup.lift()
            return

        popup = tk.Toplevel(self)
        popup.title("New Map")
        center_window(popup, 620, 340, parent=self.winfo_toplevel())
        popup.transient(self.winfo_toplevel())
        NewMapScreen(popup, on_map_created=lambda name: self._on_map_created(popup, name)).pack(
            fill="both", expand=True
        )
        self._new_map_popup = popup

    def _on_map_created(self, popup: tk.Toplevel, name: str) -> None:
        popup.destroy()
        self._new_map_popup = None
        self.refresh_configs()
        if name in self._ready:
            self._tree.selection_set(name)
            self._tree.see(name)

    def _selected_config_path(self) -> Path | None:
        name = self._selected_name()
        for display, path in self._configs:
            if display == name:
                return path
        return None

    def _skipped_steps(self) -> set[str]:
        return {step for step, var in self._skip.items() if not var.get()}

    def _on_run_pipeline(self) -> None:
        if self._running:
            return
        cfg_path = self._selected_config_path()
        if cfg_path is None:
            self._append("No map selected.", tag="error")
            return
        name = self._selected_name()
        if not self._ready.get(name, False):
            self._append(f"'{name}' isn't ready — fix its DEM/TLM data first.", tag="error")
            return

        self._tmp_config = CONFIG_DIR / f".tmp_{cfg_path.stem}.json"
        try:
            build_run_config(cfg_path, self._skipped_steps(), self._tmp_config)
        except Exception as exc:
            self._append(f"Failed to write run config: {exc}", tag="error")
            self._tmp_config = None
            return

        self._append(f"\n── Run Pipeline · {name} ──────────────────", tag="ok")
        self._set_running(True)

        cmd = [str(VENV_PYTHON), str(PIPELINE_DIR / "run_pipeline.py"), str(self._tmp_config)]
        run_subprocess(cmd, self._log_queue)
        self._poll_queue()

    def _append(self, text: str, tag: str | None = None) -> None:
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag or "")
        self._log.see("end")
        self._log.config(state="disabled")

    def _set_running(self, running: bool) -> None:
        self._running = running
        self._tree.state(("disabled",) if running else ("!disabled",))
        self._on_tree_select()

    def _poll_queue(self) -> None:
        try:
            while True:
                line = self._log_queue.get_nowait()
                if line is None:
                    self._set_running(False)
                    if self._tmp_config:
                        self._tmp_config.unlink(missing_ok=True)
                        self._tmp_config = None
                    return
                line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
                if not line:
                    continue
                tag = None
                low = line.lower()
                if "✗" in line or "failed" in low or "error" in low:
                    tag = "error"
                elif "done" in low or "ok" in low:
                    tag = "ok"
                self._append(line, tag=tag)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)
