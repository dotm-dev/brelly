# pipeline/scripts/road_graph.py
"""Build a RoadGraph from road centerline geometries."""
from dataclasses import dataclass
import hashlib
from shared.utils.coords import Config, lv95_to_enu


@dataclass
class RoadLine:
    id: str
    coords_lv95: list[tuple[float, float, float]]  # (E, N, elevation)
    width_m: float
    road_type: str = "road_local"


def _point_key(x: float, z: float, precision: float = 0.5) -> str:
    """Round-snap key for deduplicating nearby endpoints."""
    rx = round(x / precision) * precision
    rz = round(z / precision) * precision
    return f"{rx:.2f},{rz:.2f}"


def build_road_graph(roads: list[RoadLine], config: Config) -> dict:
    """Convert road centerlines to a {nodes, edges} road graph in ENU space."""
    nodes_by_key: dict[str, dict] = {}
    edges: list[dict] = []

    def get_or_create_node(e: float, n: float, elev: float) -> str:
        x, y, z = lv95_to_enu(e, n, elev, config)
        key = _point_key(x, z)
        if key not in nodes_by_key:
            node_id = hashlib.md5(key.encode()).hexdigest()[:8]
            nodes_by_key[key] = {
                "id": node_id,
                "position": {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
            }
        return nodes_by_key[key]["id"]

    for road in roads:
        if len(road.coords_lv95) < 2:
            continue
        start = road.coords_lv95[0]
        end = road.coords_lv95[-1]
        from_id = get_or_create_node(*start)
        to_id = get_or_create_node(*end)
        edges.append({
            "id": road.id,
            "fromNodeId": from_id,
            "toNodeId": to_id,
            "widthMetres": road.width_m,
            "roadType": road.road_type,
        })

    return {
        "nodes": list(nodes_by_key.values()),
        "edges": edges,
    }
