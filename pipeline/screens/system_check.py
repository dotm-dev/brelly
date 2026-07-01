# pipeline/screens/system_check.py
"""System Check screen: runs system_checks.run_all_checks() and renders a
checklist, expanding failed items with the OS-specific fix command. Each
row can be individually rechecked, and any visible fix command can be
copied to the clipboard."""
from __future__ import annotations

import platform
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from system_checks import run_all_checks, run_single_check

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
        self._last_results: list = []
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
        self._last_results = run_all_checks(project_root=PROJECT_ROOT)
        self._render_rows()

    def _render_rows(self) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()

        self._all_ok = all(r.ok for r in self._last_results)

        for result in self._last_results:
            self._build_row(result)

        self._maybe_notify_all_ok()

    def _build_row(self, result) -> None:
        row = tk.Frame(self._list_frame)
        row.pack(fill="x", pady=2, anchor="w")

        header = tk.Frame(row)
        header.pack(fill="x", anchor="w")

        icon = "✓" if result.ok else "✗"
        color = "#6a9955" if result.ok else "#f44747"
        tk.Label(header, text=f"{icon}  {result.name}", fg=color).pack(side="left")
        tk.Button(
            header, text="↻", width=2,
            command=lambda: self._recheck_one(result.name),
        ).pack(side="left", padx=(6, 0))

        if not result.ok:
            fix = result.fix_windows if self._is_windows else result.fix_macos
            if fix:
                fix_row = tk.Frame(row)
                fix_row.pack(fill="x", anchor="w")
                tk.Label(fix_row, text=f"      → {fix}", fg="#94a3b8",
                         font=("Courier", 10)).pack(side="left")
                tk.Button(
                    fix_row, text="Copy", font=("", 9),
                    command=lambda f=fix: self._copy_to_clipboard(f),
                ).pack(side="left", padx=(6, 0))

    def _recheck_one(self, name: str) -> None:
        fresh = run_single_check(name, project_root=PROJECT_ROOT)
        self._last_results = [
            fresh if r.name == name else r for r in self._last_results
        ]
        self._render_rows()

    def _copy_to_clipboard(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _maybe_notify_all_ok(self) -> None:
        if self._all_ok and self._on_all_ok:
            self._on_all_ok()
