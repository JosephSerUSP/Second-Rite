import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "semantics" / "environment_walk_surface.py"
SPEC = importlib.util.spec_from_file_location("environment_walk_surface", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class EnvironmentWalkSurfaceTests(unittest.TestCase):
    def test_compile_polygons_preserves_order_and_plane(self):
        faces = [
            [(0, 0, 1.25), (3, 0, 1.25), (3, 2, 1.25), (0, 2, 1.25)],
            [(4, 0, 1.25), (5, 0, 1.25), (4.5, 1, 1.25)],
        ]
        polygons, ground_z = MODULE.compile_polygons(faces, "walk")
        self.assertAlmostEqual(ground_z, 1.25)
        self.assertEqual(
            polygons,
            [
                {"points": [[0.0, 0.0], [3.0, 0.0], [3.0, 2.0], [0.0, 2.0]]},
                {"points": [[4.0, 0.0], [5.0, 0.0], [4.5, 1.0]]},
            ],
        )

    def test_compile_polygons_rejects_nonplanar_walk_geometry(self):
        with self.assertRaisesRegex(ValueError, "must be planar"):
            MODULE.compile_polygons(
                [[(0, 0, 0), (1, 0, 0), (0, 1, 0.2)]],
                "walk",
            )

    def test_obstacles_must_share_walk_plane(self):
        with self.assertRaisesRegex(ValueError, "must be planar"):
            MODULE.compile_polygons(
                [[(0, 0, 0.1), (1, 0, 0.1), (0, 1, 0.1)]],
                "obstacles",
                plane_z=0,
            )

    def test_compile_polygons_rejects_short_faces(self):
        with self.assertRaisesRegex(ValueError, "at least 3 vertices"):
            MODULE.compile_polygons([[(0, 0, 0), (1, 0, 0)]], "walk")


if __name__ == "__main__":
    unittest.main()
