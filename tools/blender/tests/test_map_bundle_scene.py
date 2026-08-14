import json
import pathlib
import sys
import unittest

BLENDER_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BLENDER_DIR) not in sys.path:
    sys.path.insert(0, str(BLENDER_DIR))

from map_bundle_scene import BundleError, build_scene_plan


class MapBundleSceneTests(unittest.TestCase):
    def fixture(self):
        return {
            "version": 1,
            "map": {"id": 8, "name": "Developer Room"},
            "coordinateSystem": {"handedness": "right", "up": "z", "unit": "map-cell"},
            "materials": [
                {"id": "material_001", "color": [1, 0.5, 0.25, 1]},
            ],
            "surfaces": [
                {
                    "id": "floor_1_2",
                    "name": "floor 1 2",
                    "source": {"kind": "cell", "x": 0, "y": 1, "surface": "floor"},
                    "material": "material_001",
                    "positions": [0, 0, 0, 1, 0, 0, 0, 1, 0],
                    "uvs": [0, 0, 1, 0, 0, 1],
                    "normals": [0, 0, 1] * 3,
                    "colors": [0.2, 0.3, 0.4, 1] * 3,
                },
                {
                    "id": "event_4",
                    "name": "event_4",
                    "source": {"kind": "event", "id": 4},
                    "material": "material_001",
                    "positions": [0, 0, 0, 0, 0, 1, 1, 0, 0],
                    "uvs": [0, 0, 0, 1, 1, 0],
                    "normals": [0, 1, 0] * 3,
                    "colors": [1, 1, 1, 1] * 3,
                },
            ],
        }

    def test_preserves_surface_structure_and_provenance(self):
        plan = build_scene_plan(self.fixture())
        self.assertEqual(plan["root_collection"], "Thestra_Map_8")
        self.assertEqual(plan["collections"], ["cell", "event"])
        self.assertEqual(plan["stats"], {"object_count": 2, "triangle_count": 2, "vertex_count": 6})

        floor = plan["objects"][0]
        self.assertEqual(floor["name"], "floor_1_2")
        self.assertEqual(floor["collection"], "cell")
        self.assertEqual(floor["entity_name"], "cell_0_1_floor")
        self.assertEqual(plan["objects"][1]["entity_name"], "event_4")
        self.assertEqual(floor["faces"], [(0, 1, 2)])
        self.assertEqual(floor["properties"]["thestra_source_x"], 0)
        self.assertEqual(floor["properties"]["thestra_source_surface"], "floor")
        self.assertEqual(
            json.loads(floor["properties"]["thestra_source_json"]),
            {"kind": "cell", "surface": "floor", "x": 0, "y": 1},
        )
        self.assertEqual(floor["colors"][0], (0.2, 0.3, 0.4, 1.0))

    def test_rejects_unknown_material(self):
        bundle = self.fixture()
        bundle["surfaces"][0]["material"] = "missing"
        with self.assertRaisesRegex(BundleError, "unknown material"):
            build_scene_plan(bundle)

    def test_rejects_incomplete_triangle_stream(self):
        bundle = self.fixture()
        bundle["surfaces"][0]["positions"] = [0, 0, 0, 1, 0, 0]
        bundle["surfaces"][0]["uvs"] = [0, 0, 1, 0]
        bundle["surfaces"][0]["normals"] = [0, 0, 1] * 2
        bundle["surfaces"][0]["colors"] = [1, 1, 1, 1] * 2
        with self.assertRaisesRegex(BundleError, "complete triangles"):
            build_scene_plan(bundle)

    def test_rejects_wrong_coordinate_contract(self):
        bundle = self.fixture()
        bundle["coordinateSystem"]["up"] = "y"
        with self.assertRaisesRegex(BundleError, "right-handed Z-up"):
            build_scene_plan(bundle)


if __name__ == "__main__":
    unittest.main()
