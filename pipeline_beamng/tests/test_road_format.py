import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from formats.road import decalroad_object, write_items_level_json


def test_decalroad_object_has_required_fields():
    nodes = [[0.0, 0.0, 0.0, 8.0], [50.0, 0.0, 0.0, 8.0]]
    obj = decalroad_object(name="road_1", nodes=nodes)
    assert obj["class"] == "DecalRoad"
    assert obj["name"] == "road_1"
    assert obj["nodes"] == nodes
    assert obj["material"] == "road_asphalt"
    assert obj["drivability"] == 1
    assert obj["autoLanes"] is True


def test_decalroad_object_custom_material():
    obj = decalroad_object(name="road_2", nodes=[[0, 0, 0, 4]], material="road_gravel")
    assert obj["material"] == "road_gravel"


def test_write_items_level_json_is_line_delimited(tmp_path):
    objects = [
        {"class": "TerrainBlock", "name": "t1"},
        {"class": "DecalRoad", "name": "r1"},
    ]
    out_path = tmp_path / "items.level.json"
    write_items_level_json(out_path, objects)

    lines = out_path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == objects[0]
    assert json.loads(lines[1]) == objects[1]
