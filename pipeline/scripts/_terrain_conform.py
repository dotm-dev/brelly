# pipeline/scripts/_terrain_conform.py
"""Stamp road elevations into a heightmap numpy array."""
from dataclasses import dataclass
import numpy as np
import math


@dataclass
class RoadSegment:
    points: list   # [(e, n, z), ...] in LV95 metres
    half_width: float  # metres


def _closest_point_on_segment(px, py, ax, ay, bx, by):
    """Return (closest_x, closest_y, t) where t in [0,1] along AB."""
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-10:
        return ax, ay, 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    return ax + t * dx, ay + t * dy, t


def conform_to_roads(
    arr: np.ndarray,
    segments: list,
    min_e: float,
    min_n: float,
    cell_size: float,
    blend_cells: int = 2,
) -> None:
    """Modify arr in-place: raise terrain cells to road elevation along each segment.

    arr[row, col] corresponds to:
        e = min_e + col * cell_size
        n = min_n + row * cell_size
    Only raises — never lowers — terrain (no trenching).
    """
    rows, cols = arr.shape
    blend_m = blend_cells * cell_size

    for seg in segments:
        pts = seg.points
        for i in range(len(pts) - 1):
            ax, ay, az = pts[i][0], pts[i][1], pts[i][2]
            bx, by, bz = pts[i + 1][0], pts[i + 1][1], pts[i + 1][2]

            pad = seg.half_width + blend_m
            col_lo = max(0, int((min(ax, bx) - pad - min_e) / cell_size))
            col_hi = min(cols - 1, int((max(ax, bx) + pad - min_e) / cell_size) + 1)
            row_lo = max(0, int((min(ay, by) - pad - min_n) / cell_size))
            row_hi = min(rows - 1, int((max(ay, by) + pad - min_n) / cell_size) + 1)

            if col_lo > col_hi or row_lo > row_hi:
                continue

            # Build coordinate grids for the sub-window (vectorised)
            c_idx = np.arange(col_lo, col_hi + 1)
            r_idx = np.arange(row_lo, row_hi + 1)
            cell_e = min_e + c_idx * cell_size           # shape (W,)
            cell_n = min_n + r_idx * cell_size           # shape (H,)
            E, N = np.meshgrid(cell_e, cell_n)           # shape (H, W)

            # Closest point on segment for every cell in sub-window
            dx, dy = bx - ax, by - ay
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq < 1e-10:
                t = np.zeros_like(E)
            else:
                t = np.clip(((E - ax) * dx + (N - ay) * dy) / seg_len_sq, 0.0, 1.0)

            cx = ax + t * dx
            cy = ay + t * dy
            dist = np.hypot(E - cx, N - cy)
            road_z = az + t * (bz - az)

            # Compute weights: 1 inside corridor, cosine blend outside, 0 beyond.
            # outer boundary extends blend_m + half_cell so the outermost cell centre
            # gets a non-zero weight (matches original scalar implementation).
            half_cell = 0.5 * cell_size
            outer = seg.half_width + blend_m + half_cell
            weight = np.where(
                dist <= seg.half_width,
                1.0,
                np.where(
                    dist < outer,
                    0.5 * (1.0 + np.cos(np.pi * (dist - seg.half_width) / (blend_m + half_cell))),
                    0.0,
                ),
            )

            target = arr[row_lo:row_hi + 1, col_lo:col_hi + 1] * (1.0 - weight) + road_z * weight
            # Only raise terrain, never lower
            sub = arr[row_lo:row_hi + 1, col_lo:col_hi + 1]
            np.maximum(sub, target, out=sub)
