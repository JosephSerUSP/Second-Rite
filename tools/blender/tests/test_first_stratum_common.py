"""Tests for First Stratum modeling helpers, validating box geometry and normal orientation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from first_stratum.common import box_geometry
from house_grammar.records import face_normal


class FirstStratumCommonBoxTests(unittest.TestCase):
    def test_box_geometry_normals_are_outward(self):
        # A box with asymmetric dimensions to verify coordinate alignment
        size = (2.0, 4.0, 6.0)
        vertices, faces = box_geometry(size)

        self.assertEqual(len(vertices), 8)
        self.assertEqual(len(faces), 6)

        expected_normals = [
            (0.0, 0.0, -1.0),  # 0: bottom face (-Z)
            (0.0, 0.0, 1.0),   # 1: top face (+Z)
            (0.0, -1.0, 0.0),  # 2: front face (-Y)
            (1.0, 0.0, 0.0),   # 3: right face (+X)
            (0.0, 1.0, 0.0),   # 4: back face (+Y)
            (-1.0, 0.0, 0.0),  # 5: left face (-X)
        ]

        computed_normals = [face_normal(vertices, face) for face in faces]
        for idx, (expected, computed) in enumerate(zip(expected_normals, computed_normals)):
            for axis in range(3):
                self.assertAlmostEqual(
                    expected[axis],
                    computed[axis],
                    places=6,
                    msg=f"Face {idx} axis {axis} expected {expected[axis]} but got {computed[axis]}"
                )

    def test_negative_control_inverted_winding_detects_inward_normals(self):
        # The legacy winding in issue #936 was inverted
        legacy_faces = [
            (0, 1, 2, 3),  # bottom (+Z normal, inward)
            (4, 7, 6, 5),  # top (-Z normal, inward)
            (0, 4, 5, 1),  # front (+Y normal, inward)
            (1, 5, 6, 2),  # right (-X normal, inward)
            (2, 6, 7, 3),  # back (-Y normal, inward)
            (4, 0, 3, 7),  # left (+X normal, inward)
        ]
        vertices, _ = box_geometry((1.0, 1.0, 1.0))
        for legacy_face in legacy_faces:
            normal = face_normal(vertices, legacy_face)
            if legacy_face == (0, 1, 2, 3):
                self.assertAlmostEqual(normal[2], 1.0)
            elif legacy_face == (4, 7, 6, 5):
                self.assertAlmostEqual(normal[2], -1.0)


if __name__ == "__main__":
    unittest.main()
