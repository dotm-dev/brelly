# pipeline/app.py
"""Brelly pipeline desktop app — single entry point covering system setup,
new map creation, and running the pipeline."""
from __future__ import annotations

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tkinter as tk
    from tkinter import ttk
    _TK_AVAILABLE = True
except ModuleNotFoundError:
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    _TK_AVAILABLE = False

from screens.system_check import SystemCheckScreen
from screens.run import RunScreen
from screens.ui import center_window


class App(tk.Tk if _TK_AVAILABLE else object):  # type: ignore[misc]
    def __init__(self) -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError("tkinter is not available in this Python environment.")
        super().__init__()
        self.title("Brelly Pipeline")
        center_window(self, 760, 560)
        self.minsize(560, 420)

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True)

        self._system_tab = SystemCheckScreen(self._notebook, on_all_ok=self._on_system_ok)
        self._run_tab = RunScreen(self._notebook)

        self._notebook.add(self._system_tab, text="System Check")
        self._notebook.add(self._run_tab, text="Run")

        self._select_initial_tab()

    def _select_initial_tab(self) -> None:
        if not self._system_tab.all_ok():
            self._notebook.select(self._system_tab)
        else:
            self._notebook.select(self._run_tab)

    def _on_system_ok(self) -> None:
        pass  # system check passing doesn't force navigation away from wherever the user is


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
