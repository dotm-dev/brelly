import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from formats.coords import road_node_to_beamng


def test_east_stays_on_x_axis():
    bx, by, bz = road_node_to_beamng(10.0, 0.0, 0.0)
    assert bx == 10.0


def test_negated_north_becomes_positive_y():
    # road_splines.json stores z = -north (glTF convention); BeamNG Y should be +north
    bx, by, bz = road_node_to_beamng(0.0, 0.0, -25.0)
    assert by == 25.0


def test_elevation_becomes_z():
    bx, by, bz = road_node_to_beamng(0.0, 12.5, 0.0)
    assert bz == 12.5


def test_full_conversion():
    bx, by, bz = road_node_to_beamng(3.0, 4.0, -5.0)
    assert (bx, by, bz) == (3.0, 5.0, 4.0)
