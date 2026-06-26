# pipeline/scripts/_road_resampler.py
"""Distance-based resampling for road spline nodes."""
from __future__ import annotations
import math

RESAMPLE_MAX_SPACING = 2.0   # metres


def _resample_nodes(
    nodes: list[dict],
    segments: list[dict],
    max_spacing: float = RESAMPLE_MAX_SPACING,
) -> tuple[list[dict], list[dict]]:
    """Return (new_nodes, new_segments) with no consecutive gap > max_spacing.

    Nodes are interpolated linearly in 3-D glTF space (X=East, Y=elev, Z=-North).
    isLocked is False for every interpolated node.
    Each sub-segment inherits the kind of its parent segment.
    """
    if len(nodes) < 2:
        return list(nodes), list(segments)

    # Build a per-node -> kind lookup from the segment list.
    node_kind: list[str] = ["ground"] * len(nodes)
    for seg in segments:
        for idx in range(seg["startIdx"], seg["endIdx"]):
            node_kind[idx] = seg["kind"]

    new_nodes: list[dict] = []
    new_segs:  list[dict] = []

    for seg in segments:
        si = seg["startIdx"]
        ei = seg["endIdx"]
        kind = seg["kind"]
        a = nodes[si]
        b = nodes[ei]

        dx = b["x"] - a["x"]
        dy = b["y"] - a["y"]
        dz = b["z"] - a["z"]
        seg_len = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Number of sub-divisions needed.
        n_div = max(1, math.ceil(seg_len / max_spacing))

        # Emit start node (copy from input, preserve isLocked).
        if not new_nodes:
            new_nodes.append(dict(a))
        # else the start is already the last node emitted by the previous segment.

        start_idx = len(new_nodes) - 1

        for k in range(1, n_div + 1):
            t = k / n_div
            interp = {
                "x": a["x"] + t * dx,
                "y": a["y"] + t * dy,
                "z": a["z"] + t * dz,
                "isLocked": b["isLocked"] if k == n_div else False,
            }
            new_nodes.append(interp)
            new_segs.append({
                "startIdx": start_idx + k - 1,
                "endIdx":   start_idx + k,
                "kind":     kind,
            })

    return new_nodes, new_segs
