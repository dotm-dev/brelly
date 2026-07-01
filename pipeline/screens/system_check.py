# pipeline/screens/system_check.py
"""System Check screen: runs system_checks.run_all_checks() and renders a
checklist, expanding failed items with the OS-specific fix command."""
from __future__ import annotations

import platform
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from system_checks import run_all_checks

PROJECT_ROOT = Path(__file__).parent.parent.parent

try:
    import tkinter as tk
    from tkinter import ttk
    _TK_AVAILABLE = True
except ModuleNotFoundError:
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    _TK_AVAILABLE = False


class SystemCheckScreen(tk.Frame if _TK_AVAILABLE else object):  # type: ignore[misc]
    def __init__(self, parent, on_all_ok=None) -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError("tkinter is not available in this Python environment.")
        super().__init__(parent)
        self._on_all_ok = on_all_ok
        self._is_windows = platform.system() == "Windows"
        self._build_ui()
        self.recheck()

    def _build_ui(self) -> None:
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        tk.Label(top, text="System Check", font=("", 13, "bold")).pack(side="left")
        tk.Button(top, text="Recheck", command=self.recheck).pack(side="right")

        self._list_frame = tk.Frame(self)
        self._list_frame.pack(fill="both", expand=True, padx=8, pady=6)

    def all_ok(self) -> bool:
        return self._all_ok

    def recheck(self) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()

        results = run_all_checks(project_root=PROJECT_ROOT)
        self._all_ok = all(r.ok for r in results)

        for result in results:
            row = tk.Frame(self._list_frame)
            row.pack(fill="x", pady=2, anchor="w")
            icon = "✓" if result.ok else "✗"
            color = "#6a9955" if result.ok else "#f44747"
            tk.Label(row, text=f"{icon}  {result.name}", fg=color).pack(anchor="w")
            if not result.ok:
                fix = result.fix_windows if self._is_windows else result.fix_macos
                if fix:
                    tk.Label(row, text=f"      → {fix}", fg="#94a3b8",
                             font=("Courier", 10)).pack(anchor="w")

        if self._all_ok and self._on_all_ok:
            self._on_all_ok()
