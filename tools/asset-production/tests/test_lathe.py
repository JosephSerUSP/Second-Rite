"""Geometry and failure-mode tests for the profile lathe.

The lathe exists to replace hand-built solids that all collapsed to the same
box, so the tests that matter most are the ones proving two different profiles
produce two different shapes, and that a malformed profile fails instead of
quietly producing something.
"""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools" / "asset-production"))

import item_model_corpus  # noqa: E402
import lathe as lathe_mod  # noqa: E402

# A closed cylinder: flat bottom, straight side, flat top.
CYLINDER = [(-1.0, 0.5), (1.0, 0.5)]
# A teardrop: capped bottom, belly, closed on the axis at the top.
TEARDROP = [(-1.0, 0.0), (-0.6, 0.55), (0.2, 0.6), (1.0, 0.0)]


class ProfileValidationTests(unittest.TestCase):
    def test_single_point_profile_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe([(0.0, 1.0)])

    def test_unsorted_profile_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe([(1.0, 0.5), (-1.0, 0.5)])

    def test_negative_radius_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe([(-1.0, 0.5), (1.0, -0.2)])

    def test_zero_height_profile_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe([(0.0, 0.5), (0.0, 0.9)])

    def test_profile_entirely_on_the_axis_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe([(-1.0, 0.0), (1.0, 0.0)])

    def test_non_finite_point_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe([(-1.0, 0.5), (float("inf"), 0.5)])

    def test_too_few_segments_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe(CYLINDER, segments=2)

    def test_material_count_must_match_band_count(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe(TEARDROP, materials=["crystal", "wax"])  # 3 bands


class GeometryTests(unittest.TestCase):
    def test_cylinder_radius_and_height_match_the_profile(self):
        mesh = lathe_mod.lathe(CYLINDER, segments=32)
        for x, y, z in mesh.vertices:
            radius = math.hypot(x, z)
            self.assertLessEqual(radius, 0.5 + 1e-9)
            self.assertGreaterEqual(y, -1.0 - 1e-9)
            self.assertLessEqual(y, 1.0 + 1e-9)
        (_, min_y, _), (_, max_y, _) = mesh.bounds()
        self.assertAlmostEqual(min_y, -1.0)
        self.assertAlmostEqual(max_y, 1.0)

    def test_every_face_carries_uvs(self):
        """The whole point of lathing is that UVs come free."""
        mesh = lathe_mod.lathe(TEARDROP, segments=16)
        self.assertTrue(mesh.faces)
        for _, corners in mesh.faces:
            for _, uv_index in corners:
                self.assertLess(uv_index, len(mesh.uvs))
        us = [u for u, _ in mesh.uvs]
        vs = [v for _, v in mesh.uvs]
        self.assertGreaterEqual(min(us), 0.0)
        self.assertLessEqual(max(us), 1.0)
        self.assertAlmostEqual(min(vs), 0.0)
        self.assertAlmostEqual(max(vs), 1.0)

    def test_axis_point_collapses_to_one_vertex_not_a_ring(self):
        mesh = lathe_mod.lathe(TEARDROP, segments=12)
        poles = [v for v in mesh.vertices if math.hypot(v[0], v[2]) < 1e-9]
        # Two axis points in the profile, plus the bottom cap centre is absent
        # because the bottom is already closed on the axis.
        self.assertEqual(len(poles), 2)

    def test_no_degenerate_faces(self):
        for profile in (CYLINDER, TEARDROP):
            mesh = lathe_mod.lathe(profile, segments=20)
            for material, corners in mesh.faces:
                indices = [v for v, _ in corners]
                self.assertEqual(
                    len(set(indices)), len(indices), f"{material}: repeated vertex {corners}"
                )

    def test_partial_sweep_produces_an_open_form(self):
        full = lathe_mod.lathe(CYLINDER, segments=24, sweep=1.0)
        half = lathe_mod.lathe(CYLINDER, segments=24, sweep=0.5)
        (min_x, _, min_z), (max_x, _, max_z) = half.bounds()
        self.assertLess(min_z, 1e-9)  # only one side of the axis is swept
        self.assertNotEqual(len(full.vertices), len(half.vertices))

    def test_per_band_materials_land_on_the_right_faces(self):
        mesh = lathe_mod.lathe(
            TEARDROP, segments=8, materials=["crystal", "wax", "ritual_gold"]
        )
        used = {material for material, _ in mesh.faces}
        self.assertEqual(used, {"crystal", "wax", "ritual_gold"})


def circle_profile(centre_radius=1.0, tube=0.18, points=12):
    return [
        (tube * math.sin(i / points * math.tau), centre_radius + tube * math.cos(i / points * math.tau))
        for i in range(points)
    ]


class ClosedProfileTests(unittest.TestCase):
    """Rings and beads are tori; a monotonic profile cannot express one."""

    def test_a_ring_cross_section_is_rejected_as_an_open_profile(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe(circle_profile())

    def test_the_same_profile_lathes_when_declared_closed(self):
        mesh = lathe_mod.lathe(circle_profile(), segments=16, closed_profile=True)
        self.assertTrue(mesh.faces)

    def test_a_closed_profile_touching_the_axis_is_rejected(self):
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.lathe(circle_profile(centre_radius=0.18), closed_profile=True)

    def test_closed_profile_leaves_a_hole_on_the_axis(self):
        """The defining property of a ring: nothing at the centre."""
        mesh = lathe_mod.lathe(circle_profile(tube=0.2), segments=24, closed_profile=True)
        nearest = min(math.hypot(x, z) for x, y, z in mesh.vertices)
        self.assertGreater(nearest, 0.7)

    def test_closed_profile_grows_no_caps(self):
        """A cap on a closed profile would be a disc through the ring."""
        mesh = lathe_mod.lathe(circle_profile(), segments=12, closed_profile=True)
        on_axis = [v for v in mesh.vertices if math.hypot(v[0], v[2]) < 1e-9]
        self.assertEqual(on_axis, [])

    def test_a_ring_and_a_bead_are_distinct_to_the_gate(self):
        import check_item_models

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            models = {}
            for name, kwargs in (
                ("Slim Ring", dict(centre_radius=1.0, tube=0.12)),
                ("Fat Bead", dict(centre_radius=0.55, tube=0.4)),
            ):
                mesh = lathe_mod.lathe(
                    circle_profile(**kwargs),
                    segments=20,
                    name=name.replace(" ", "_"),
                    material="ritual_gold",
                    closed_profile=True,
                )
                path = directory / f"{name.replace(' ', '_')}.obj"
                lathe_mod.write_obj(mesh, path, mtllib="test.mtl")
                models[name] = path
            self.assertEqual(check_item_models.collect_violations(models), [])


class CorpusCompatibilityTests(unittest.TestCase):
    """A lathed mesh must satisfy the gate it was built to satisfy."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _export(self, name, profile, **kwargs):
        mesh = lathe_mod.lathe(profile, name=name, **kwargs)
        path = self.dir / f"{name}.obj"
        lathe_mod.write_obj(mesh, path, mtllib="test.mtl")
        return path

    def test_exported_obj_parses_and_reports_uvs(self):
        path = self._export("cyl", CYLINDER, segments=16, material="crystal")
        mesh = item_model_corpus.parse_obj(path)
        self.assertGreater(mesh.faces_with_uv, 0)

    def test_two_different_profiles_are_distinct_to_the_gate(self):
        import check_item_models

        models = {
            "Cylinder": self._export("cyl", CYLINDER, segments=16, material="crystal"),
            "Teardrop": self._export("drop", TEARDROP, segments=16, material="crystal"),
        }
        self.assertEqual(check_item_models.collect_violations(models), [])

    def test_unregistered_material_fails_loudly(self):
        mesh = lathe_mod.lathe(CYLINDER, material="unobtainium")
        with self.assertRaises(lathe_mod.LatheError):
            lathe_mod.write_obj(mesh, self.dir / "x.obj", mtllib="test.mtl")


if __name__ == "__main__":
    unittest.main()
