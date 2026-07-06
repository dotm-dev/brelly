# pipeline/tests/test_road_graph.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))                # repo root, for shared/
from scripts.road_graph import build_road_graph, RoadLine
from shared.utils.coords import Config


CONFIG = Config(center_e=2683000.0, center_n=1247500.0, base_elevation=450.0)


def test_single_road_produces_two_nodes_one_edge():
    roads = [
        RoadLine(
            id="r1",
            coords_lv95=[(2683000.0, 1247450.0, 450.0), (2683000.0, 1247550.0, 450.0)],
            width_m=6.0,
        )
    ]
    graph = build_road_graph(roads, CONFIG)
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1


def test_edge_connects_correct_nodes():
    roads = [
        RoadLine(
            id="r1",
            coords_lv95=[(2683000.0, 1247450.0, 450.0), (2683000.0, 1247550.0, 450.0)],
            width_m=6.0,
        )
    ]
    graph = build_road_graph(roads, CONFIG)
    edge = graph["edges"][0]
    node_ids = {n["id"] for n in graph["nodes"]}
    assert edge["fromNodeId"] in node_ids
    assert edge["toNodeId"] in node_ids


def test_edge_width_matches_road():
    roads = [
        RoadLine(
            id="r1",
            coords_lv95=[(2683000.0, 1247450.0, 450.0), (2683000.0, 1247550.0, 450.0)],
            width_m=8.0,
        )
    ]
    graph = build_road_graph(roads, CONFIG)
    assert graph["edges"][0]["widthMetres"] == 8.0


def test_shared_endpoint_produces_single_node():
    roads = [
        RoadLine(
            id="r1",
            coords_lv95=[(2683000.0, 1247450.0, 450.0), (2683000.0, 1247500.0, 450.0)],
            width_m=6.0,
        ),
        RoadLine(
            id="r2",
            coords_lv95=[(2683000.0, 1247500.0, 450.0), (2683000.0, 1247550.0, 450.0)],
            width_m=6.0,
        ),
    ]
    graph = build_road_graph(roads, CONFIG)
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2


def test_node_positions_are_in_enu():
    roads = [
        RoadLine(
            id="r1",
            coords_lv95=[(2683100.0, 1247500.0, 460.0), (2683200.0, 1247500.0, 460.0)],
            width_m=6.0,
        )
    ]
    graph = build_road_graph(roads, CONFIG)
    positions = [n["position"] for n in graph["nodes"]]
    assert any(abs(p["x"] - 100.0) < 1e-3 and abs(p["y"] - 10.0) < 1e-3 for p in positions)
