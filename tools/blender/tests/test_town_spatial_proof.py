import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools" / "blender" / "town_spatial_proof.py"
FIXTURE = ROOT / "tools" / "blender" / "fixtures" / "town_spatial_proof.json"
SPEC = importlib.util.spec_from_file_location("town_spatial_proof", SCRIPT)
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


class TownSpatialProofTests(unittest.TestCase):
    def test_fixture_declares_asymmetric_spatial_evidence(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        source = fixture["source"]
        self.assertNotEqual(source["anchor"][1], 0.0)
        self.assertNotEqual(source["occludedTarget"][1], source["occluder"]["center"][1])
        self.assertNotEqual(source["elevationGround"][2], source["elevationRaised"][2])
        self.assertEqual(len(source["triangle"]["vertices"]), 3)

    def test_reflection_changes_screen_order_without_projection_math(self):
        direct = proof.lane_transform((4.0, 1.0, 0.0), 0.0, False)
        reflected = proof.lane_transform((4.0, 1.0, 0.0), 0.0, True)
        self.assertEqual(direct, (4.0, 1.0, 0.0))
        self.assertEqual(reflected, (4.0, -1.0, 0.0))

    def test_reflection_reverses_winding_and_normal_lane_component(self):
        vertices = [(4.0, -2.0, 0.0), (4.0, -1.0, 1.0), (4.0, 0.0, 0.0)]
        normal = proof.normal_for_triangle(vertices)
        reflected_vertices = proof.reverse_winding(
            [proof.lane_transform(point, 0.0, True) for point in vertices], True)
        reflected_normal = proof.normal_for_triangle(reflected_vertices)
        self.assertEqual(normal[0], reflected_normal[0])
        self.assertEqual(normal[1], reflected_normal[1])
        self.assertEqual(normal[2], reflected_normal[2])
        self.assertEqual(proof.transform_normal(normal, True)[0], normal[0])
        self.assertEqual(proof.transform_normal(normal, True)[1], -normal[1])

    def test_adapter_discrepancy_is_recorded_as_data(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        interior = fixture["adapterEvidence"]["interiorCurrent"]
        exterior = fixture["adapterEvidence"]["exteriorCurrent"]
        self.assertNotEqual(interior["transform"], exterior["transform"])
        self.assertTrue(interior["reversesFaceWinding"])
        self.assertFalse(exterior["reversesFaceWinding"])
        self.assertEqual(
            fixture["adapterEvidence"]["proposedCommonAdapter"]["transform"],
            "engine_y = laneOriginY - blender_y",
        )


if __name__ == "__main__":
    unittest.main()
