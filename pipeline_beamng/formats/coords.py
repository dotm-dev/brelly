"""Convert road_splines.json node coordinates (glTF convention: x=east,
y=elevation-relative-to-base, z=-north) into BeamNG's Z-up world frame
(x=east, y=north, z=elevation-relative-to-base)."""


def road_node_to_beamng(x: float, y: float, z: float) -> tuple[float, float, float]:
    return x, -z, y
