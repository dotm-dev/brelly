# pipeline/app.py
"""Brelly pipeline desktop runner."""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PIPELINE_DIR = Path(__file__).parent
CONFIG_DIR = PIPELINE_DIR / "config"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"

STEPS = [
    "download",
    "reproject",
    "terrain",
    "roads",
    "buildings",
    "vegetation",
    "road graph",
    "manifest",
    "compress",
]


def scan_configs(config_dir: Path) -> list[tuple[str, Path]]:
    """Return [(display_name, path), ...] sorted by display name, excluding example.json."""
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


def run_subprocess(
    cmd: list[str],
    out_queue: "queue.Queue[str | None]",
) -> None:
    """Run cmd in a background thread, put each output line into out_queue. Puts None when done."""
    def _target() -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(PROJECT_ROOT),
            )
            if proc.stdout is None:
                raise RuntimeError("Popen stdout is None — unexpected")
            for line in proc.stdout:
                out_queue.put(line.rstrip("\n"))
            proc.wait()
            if proc.returncode != 0:
                out_queue.put(f"✗ process exited with code {proc.returncode}")
            out_queue.put(None)  # sentinel: done
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


class PipelineApp(tk.Tk if _TK_AVAILABLE else object):  # type: ignore[misc]
    def __init__(self) -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError("tkinter is not available in this Python environment.")
        super().__init__()
        self.title("Brelly Pipeline")
        self.geometry("720x520")
        self.minsize(480, 360)
        self.resizable(True, True)

        self._configs: list[tuple[str, Path]] = scan_configs(CONFIG_DIR)
        self._skip: dict[str, tk.BooleanVar] = {}
        self._running = False
        self._log_queue: queue.Queue[str | None] = queue.Queue()
        self._tmp_config: Path | None = None

        self._build_ui()
        self._check_venv()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 6}

        # Top bar
        top = tk.Frame(self)
        top.pack(fill="x", **pad)

        tk.Label(top, text="Map:").pack(side="left")
        self._map_var = tk.StringVar()
        names = [c[0] for c in self._configs]
        self._map_combo = ttk.Combobox(
            top, textvariable=self._map_var, values=names, state="readonly", width=18
        )
        if names:
            self._map_combo.current(0)
        self._map_combo.pack(side="left", padx=(4, 16))

        self._btn_check = tk.Button(
            top, text="Check System", command=self._on_check_system, width=14
        )
        self._btn_check.pack(side="left", padx=4)

        self._btn_run = tk.Button(
            top, text="Run Pipeline", command=self._on_run_pipeline,
            width=14, bg="#2d6a2d", activebackground="#3a8a3a",
        )
        self._btn_run.pack(side="left", padx=4)

        if not self._configs:
            self._btn_run.config(state="disabled")

        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8)

        # Step checkboxes
        steps_frame = tk.LabelFrame(self, text="Steps", padx=8, pady=4)
        steps_frame.pack(fill="x", padx=8, pady=(4, 2))

        for i, step in enumerate(STEPS):
            var = tk.BooleanVar(value=True)
            self._skip[step] = var
            cb = tk.Checkbutton(steps_frame, text=step, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=6, pady=2)

        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=(4, 0))

        # Log pane
        self._log = scrolledtext.ScrolledText(
            self, font=("Courier", 11), wrap="word", state="disabled",
            bg="#1e1e1e", fg="#d4d4d4",
        )
        self._log.pack(fill="both", expand=True, padx=8, pady=6)
        self._log.tag_config("error", foreground="#f44747")
        self._log.tag_config("ok", foreground="#6a9955")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _check_venv(self) -> None:
        if not VENV_PYTHON.exists():
            self._append(
                "WARNING: .venv not found. Run setup first: bash pipeline/check_system.sh",
                tag="error",
            )

    def _append(self, text: str, tag: str | None = None) -> None:
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag or "")
        self._log.see("end")
        self._log.config(state="disabled")

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = "disabled" if running else "normal"
        self._btn_check.config(state=state)
        self._btn_run.config(state=state)
        self._map_combo.config(state="disabled" if running else "readonly")

    def _selected_config_path(self) -> Path | None:
        name = self._map_var.get()
        for display, path in self._configs:
            if display == name:
                return path
        return None

    def _skipped_steps(self) -> set[str]:
        return {step for step, var in self._skip.items() if not var.get()}

    # ── Button handlers ──────────────────────────────────────────────────────

    def _on_check_system(self) -> None:
        if self._running:
            return
        self._append("\n── Check System ──────────────────────────────", tag="ok")
        self._set_running(True)
        run_subprocess(["bash", str(PIPELINE_DIR / "check_system.sh")], self._log_queue)
        self._poll_queue()

    def _on_run_pipeline(self) -> None:
        if self._running:
            return
        cfg_path = self._selected_config_path()
        if cfg_path is None:
            self._append("No config selected.", tag="error")
            return

        self._tmp_config = CONFIG_DIR / f".tmp_{cfg_path.stem}.json"
        try:
            build_run_config(cfg_path, self._skipped_steps(), self._tmp_config)
        except Exception as exc:
            self._append(f"Failed to write run config: {exc}", tag="error")
            self._tmp_config = None
            return

        self._append(f"\n── Run Pipeline · {self._map_var.get()} ──────────────────", tag="ok")
        self._set_running(True)

        cmd = [str(VENV_PYTHON), str(PIPELINE_DIR / "run_pipeline.py"), str(self._tmp_config)]
        run_subprocess(cmd, self._log_queue)
        self._poll_queue()

    # ── Queue polling ─────────────────────────────────────────────────────────

    def _poll_queue(self) -> None:
        try:
            while True:
                line = self._log_queue.get_nowait()
                if line is None:
                    # subprocess done
                    self._set_running(False)
                    if self._tmp_config:
                        self._tmp_config.unlink(missing_ok=True)
                        self._tmp_config = None
                    return
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


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = PipelineApp()
    app.mainloop()


if __name__ == "__main__":
    main()
