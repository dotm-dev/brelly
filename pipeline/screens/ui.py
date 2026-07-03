# pipeline/screens/ui.py
"""Small shared Tk helpers for the pipeline app windows."""
from __future__ import annotations


def center_window(win, width: int, height: int, parent=None) -> None:
    """Size win and center it — over parent if given, else on the screen.

    Clamps the position so the window never opens off-screen (e.g. when a
    parent sits near a screen edge)."""
    win.update_idletasks()
    if parent is not None:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
    else:
        x = (win.winfo_screenwidth() - width) // 2
        y = (win.winfo_screenheight() - height) // 2
    x = max(0, min(x, win.winfo_screenwidth() - width))
    y = max(0, min(y, win.winfo_screenheight() - height))
    win.geometry(f"{width}x{height}+{x}+{y}")
