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

            for r in range(row_lo, row_hi + 1):
                for c in range(col_lo, col_hi + 1):
                    cell_e = min_e + c * cell_size
                    cell_n = min_n + r * cell_size
                    cx, cy, t = _closest_point_on_segment(cell_e, cell_n, ax, ay, bx, by)
                    dist = math.hypot(cell_e - cx, cell_n - cy)
                    road_z = az + t * (bz - az)

                    # outer boundary: blend extends blend_cells full cells beyond road edge
                    # use blend_m + half_cell so the outermost cell centre gets non-zero weight
                    outer = seg.half_width + blend_m + 0.5 * cell_size
                    if dist <= seg.half_width:
                        weight = 1.0
                    elif dist < outer:
                        t_blend = (dist - seg.half_width) / (blend_m + 0.5 * cell_size)
                        weight = 0.5 * (1.0 + math.cos(math.pi * t_blend))
                    else:
                        continue

                    target = arr[r, c] * (1.0 - weight) + road_z * weight
                    if target > arr[r, c]:
                        arr[r, c] = target
