# pipeline/utils/constants.py
"""Shared numeric constants for the Brelly pipeline.

All elevation lifts are in metres above the surveyed TLM elevation and exist
to absorb the small disagreement between the TLM vector dataset and the DEM
raster at any given point.
"""

# Metres to lift road surfaces above the DEM surface at each edge vertex.
# Small value is fine because we now sample the DEM per-vertex (not per-centerline),
# so roads follow the terrain cross-section and only need a thin z-fighting buffer.
ROAD_LIFT = 0.8

# Max miter-joint scale before clamping (avoids needle spikes on sharp corners).
MAX_ROAD_MITER = 3.0

# Metres to lift tree base above the DEM surface (roots slightly above ground).
TREE_LIFT = 0.1

# Cone tree geometry
TREE_HEIGHT  = 4.0   # metres
TREE_RADIUS  = 1.5   # metres at base
TREE_SIDES   = 8     # polygon count for cone
