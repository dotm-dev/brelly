import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import math
from scripts._road_resampler import _resample_nodes


def _dist(a, b):
    return math.sqrt((b["x"]-a["x"])**2 + (b["y"]-a["y"])**2 + (b["z"]-a["z"])**2)


def test_single_node_returns_unchanged():
    nodes = [{"x": 1.0, "y": 2.0, "z": 3.0, "isLocked": True}]
    new_nodes, new_segs = _resample_nodes(nodes, [], max_spacing=2.0)
    assert new_nodes == nodes
    assert new_segs == []


def test_short_segment_unchanged():
    nodes = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "isLocked": True},
        {"x": 1.5, "y": 0.0, "z": 0.0, "isLocked": False},
    ]
    segments = [{"startIdx": 0, "endIdx": 1, "kind": "ground"}]
    new_nodes, new_segs = _resample_nodes(nodes, segments, max_spacing=2.0)
    assert len(new_nodes) == 2
    assert len(new_segs) == 1
    assert new_nodes[0] == nodes[0]
    assert new_nodes[1] == nodes[1]


def test_long_segment_is_split():
    nodes = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "isLocked": True},
        {"x": 10.0, "y": 0.0, "z": 0.0, "isLocked": True},
    ]
    segments = [{"startIdx": 0, "endIdx": 1, "kind": "ground"}]
    new_nodes, new_segs = _resample_nodes(nodes, segments, max_spacing=2.0)
    assert len(new_nodes) == 6
    assert len(new_segs) == 5


def test_max_gap_never_exceeded():
    nodes = [
        {"x": 0.0, "y": 0.0, "z":  0.0, "isLocked": True},
        {"x": 7.3, "y": 0.5, "z": -3.1, "isLocked": False},
        {"x": 7.3, "y": 0.5, "z": -9.9, "isLocked": True},
    ]
    segments = [
        {"startIdx": 0, "endIdx": 1, "kind": "ground"},
        {"startIdx": 1, "endIdx": 2, "kind": "bridge"},
    ]
    new_nodes, _ = _resample_nodes(nodes, segments, max_spacing=2.0)
    for a, b in zip(new_nodes, new_nodes[1:]):
        assert _dist(a, b) <= 2.0 + 1e-6, f"Gap {_dist(a,b):.3f} exceeds max_spacing"


def test_kind_propagated_to_sub_segments():
    nodes = [
        {"x":  0.0, "y": 0.0, "z": 0.0, "isLocked": True},
        {"x": 10.0, "y": 0.0, "z": 0.0, "isLocked": True},
    ]
    segments = [{"startIdx": 0, "endIdx": 1, "kind": "bridge"}]
    _, new_segs = _resample_nodes(nodes, segments, max_spacing=2.0)
    assert all(s["kind"] == "bridge" for s in new_segs)


def test_original_endpoint_coordinates_preserved():
    nodes = [
        {"x": 1.1, "y": 2.2, "z": 3.3, "isLocked": True},
        {"x": 4.4, "y": 5.5, "z": 6.6, "isLocked": True},
    ]
    segments = [{"startIdx": 0, "endIdx": 1, "kind": "ground"}]
    new_nodes, _ = _resample_nodes(nodes, segments, max_spacing=1.0)
    assert new_nodes[0]["x"] == 1.1
    assert new_nodes[0]["y"] == 2.2
    assert new_nodes[0]["z"] == 3.3
    assert new_nodes[-1]["x"] == 4.4
    assert new_nodes[-1]["y"] == 5.5
    assert new_nodes[-1]["z"] == 6.6


def test_isLocked_false_on_interpolated_nodes():
    nodes = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "isLocked": True},
        {"x": 6.0, "y": 0.0, "z": 0.0, "isLocked": True},
    ]
    segments = [{"startIdx": 0, "endIdx": 1, "kind": "ground"}]
    new_nodes, _ = _resample_nodes(nodes, segments, max_spacing=2.0)
    interior = new_nodes[1:-1]
    assert all(not nd["isLocked"] for nd in interior)
