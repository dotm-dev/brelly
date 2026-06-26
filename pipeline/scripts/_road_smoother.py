# pipeline/scripts/_road_smoother.py
"""Road smoothing pipeline: intersection locking → constrained Laplacian → bridge/tunnel classification.

All internal calculations work in LV95 absolute elevation (metres).
JSON output uses glTF convention: x=East, y=local_elevation, z=−North.
"""
from __future__ import annotations
from dataclasses import dataclass, field

# ── Tuning constants ──────────────────────────────────────────────────────────
LAPLACIAN_ITERS  = 10      # number of smoothing passes
LAPLACIAN_ALPHA  = 0.35    # strength per pass (0 = no smoothing, 1 = full average)
CLAMP_DELTA      = 4.0     # max metres smoothed Y may deviate from raw terrain
BRIDGE_THRESHOLD = 3.0     # road > terrain by this many metres → bridge
TUNNEL_THRESHOLD = 1.0     # road < terrain by this many metres → tunnel
SNAP_PRECISION   = 0.5     # metres: rounding tolerance for intersection detection


# ── Internal helpers ──────────────────────────────────────────────────────────

def _pt_key(e: float, n: float) -> str:
    re = round(e / SNAP_PRECISION) * SNAP_PRECISION
    rn = round(n / SNAP_PRECISION) * SNAP_PRECISION
    return f"{re:.2f},{rn:.2f}"


def _sample_dem(dem_ds, e: float, n: float, fallback: float) -> float:
    """Return absolute LV95 elevation at (e, n) from an open GDAL dataset."""
    if dem_ds is None:
        return fallback
    try:
        gt  = dem_ds.GetGeoTransform()
        col = (e - gt[0]) / gt[1]
        row = (n - gt[3]) / gt[5]
        ci, ri = int(col), int(row)
        w, h = dem_ds.RasterXSize, dem_ds.RasterYSize
        if not (0 <= ci < w and 0 <= ri < h):
            return fallback
        val = float(dem_ds.GetRasterBand(1).ReadAsArray(ci, ri, 1, 1)[0][0])
        nd  = dem_ds.GetRasterBand(1).GetNoDataValue()
        if nd is not None and abs(val - nd) < 1:
            return fallback
        return val
    except Exception:
        return fallback


# ── Public API ────────────────────────────────────────────────────────────────

def smooth_roads(roads: list, config, dem_ds) -> tuple[list[dict], list]:
    """Smooth road elevations and classify segments.

    Args:
        roads:   list of RoadLine objects (coords_lv95, width_m, road_type, id).
        config:  Config with center_e, center_n, base_elevation.
        dem_ds:  Open GDAL dataset for the DEM, or None.

    Returns:
        (spline_dicts, road_segments) where:
            spline_dicts  – JSON-ready list of smoothed spline objects.
            road_segments – list of RoadSegment objects for terrain cut/fill
                            (bridge/tunnel segments excluded).
    """
    from scripts._terrain_conform import RoadSegment

    # ── Step 1: Intersection detection ───────────────────────────────────────
    # Map point_key → [(road_idx, node_idx, abs_elev), ...]  for endpoints only.
    endpoint_map: dict[str, list[tuple[int, int, float]]] = {}
    for ri, road in enumerate(roads):
        coords = road.coords_lv95
        for ni in (0, len(coords) - 1):
            e, n, elev = coords[ni]
            key = _pt_key(e, n)
            endpoint_map.setdefault(key, []).append((ri, ni, elev))

    # Canonical elevation per intersection: unweighted mean of arriving roads.
    canonical_elev: dict[str, float] = {
        key: sum(elev for _, _, elev in entries) / len(entries)
        for key, entries in endpoint_map.items()
        if len(entries) >= 2
    }

    spline_dicts: list[dict] = []
    road_segments: list = []

    for road in roads:
        coords = road.coords_lv95   # [(e, n, abs_elev), ...]
        n_pts  = len(coords)
        if n_pts < 2:
            continue

        # ── Step 2: Build locked elevation array ─────────────────────────────
        y      = [c[2] for c in coords]   # working absolute elevations
        locked = [False] * n_pts

        # Lock nodes that participate in intersections.
        for ni in range(n_pts):
            e, n, _ = coords[ni]
            key = _pt_key(e, n)
            if key in canonical_elev:
                y[ni]      = canonical_elev[key]
                locked[ni] = True

        # Endpoints are always locked (they terminate the spline).
        locked[0]  = True
        locked[-1] = True

        # Sample raw terrain elevation for clamping.
        terrain_abs = [
            _sample_dem(dem_ds, e, n, elev)
            for e, n, elev in coords
        ]

        # ── Step 3: Constrained Laplacian smoothing (Y only) ─────────────────
        for _ in range(LAPLACIAN_ITERS):
            new_y = y[:]
            for ni in range(1, n_pts - 1):
                if locked[ni]:
                    continue
                smoothed = y[ni] + LAPLACIAN_ALPHA * (y[ni - 1] - 2 * y[ni] + y[ni + 1])
                lo = terrain_abs[ni] - CLAMP_DELTA
                hi = terrain_abs[ni] + CLAMP_DELTA
                new_y[ni] = max(lo, min(hi, smoothed))
            y = new_y

        # ── Step 4: Classify segments + build output structures ───────────────
        nodes_json: list[dict] = []
        for ni, (e, n, _) in enumerate(coords):
            # glTF convention: X=East, Y=local_elev, Z=−North
            x_gltf =  e - config.center_e
            y_gltf =  y[ni] - config.base_elevation
            z_gltf = -(n - config.center_n)
            nodes_json.append({
                "x": round(x_gltf, 3),
                "y": round(y_gltf, 3),
                "z": round(z_gltf, 3),
                "isLocked": locked[ni],
            })

        segments_json: list[dict] = []
        for si in range(n_pts - 1):
            mid_e   = (coords[si][0] + coords[si + 1][0]) / 2
            mid_n   = (coords[si][1] + coords[si + 1][1]) / 2
            mid_abs = (y[si]         + y[si + 1])         / 2
            t_abs   = _sample_dem(dem_ds, mid_e, mid_n, mid_abs)
            delta   = mid_abs - t_abs

            if delta > BRIDGE_THRESHOLD:
                kind = "bridge"
            elif delta < -TUNNEL_THRESHOLD:
                kind = "tunnel"
            else:
                kind = "ground"

            segments_json.append({"startIdx": si, "endIdx": si + 1, "kind": kind})

        spline_dicts.append({
            "id":          road.id,
            "roadType":    road.road_type,
            "widthMetres": road.width_m,
            "nodes":       nodes_json,
            "segments":    segments_json,
        })

        # Only emit ground segments for terrain deformation.
        ground_pts: list[tuple[float, float, float]] = []
        prev_kind: str | None = None

        def _flush(pts):
            if len(pts) >= 2:
                road_segments.append(RoadSegment(points=list(pts), half_width=road.width_m / 2))

        for si, seg in enumerate(segments_json):
            e0, n0 = coords[si][0],     coords[si][1]
            e1, n1 = coords[si + 1][0], coords[si + 1][1]
            z0_local = y[si]     - config.base_elevation
            z1_local = y[si + 1] - config.base_elevation

            if seg["kind"] == "ground":
                if not ground_pts:
                    ground_pts.append((e0, n0, z0_local))
                ground_pts.append((e1, n1, z1_local))
            else:
                _flush(ground_pts)
                ground_pts = []

        _flush(ground_pts)

    return spline_dicts, road_segments
