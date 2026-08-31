"""The seam normalizer, refusals first.

`docs/design/st-maria-seam-defect.md` specifies one repair and five things that
merely look like it. The refusals are asserted before the repairs on purpose: a
normalizer that repairs everything passes every positive test in this file
while quietly reshaping the buildings it exists to compare against. The
positive cases alone cannot tell the two apart.

The two repair cases reproduce the measurements taken from
`st_maria_praca.blend` -- `ARCH_west_house` v36 at -0.07 in X off a clean seam,
and `ARCH_west_house.006` v36 at -0.07 in Y off a seam that is itself drifted
1.7 mm from its nominal plane. The second is the one that decides the design:
it is why the seam is the coordinate the cohort agrees on rather than the one
the modifier nominates.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar import seam  # noqa: E402


def box(x0, x1, y0=115.0, y1=120.0, z0=0.0, z1=5.0):
    """Eight vertices and six faces. Vertices 4..7 carry the +X face."""
    vertices = [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1),
                (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7),
             (0, 3, 7, 4), (1, 5, 6, 2)]
    return vertices, faces


def displace(vertices, index, axis, value):
    moved = [list(vertex) for vertex in vertices]
    moved[index][axis] = value
    return [tuple(vertex) for vertex in moved]


class RefusalTests(unittest.TestCase):
    """Everything that resembles the defect and is not it."""

    def test_a_clean_seam_is_left_alone(self):
        vertices, faces = box(14.0, 16.0)
        self.assertEqual(seam.find_defects(vertices, faces, 0, 16.0), [])

    def test_a_uniformly_drifted_seam_is_left_alone(self):
        # ARCH_west_house.006's real state: the whole loop 1.7 mm off its
        # nominal plane. Every vertex shares the drift, so the seam is still a
        # coherent loop and the mirror still welds it. Keying on the nominal
        # plane would drag the building's seam sideways to "fix" it.
        vertices, faces = box(14.0, 16.0)
        for index in (4, 5, 6, 7):
            vertices = displace(vertices, index, 0, 16.0017)
        self.assertEqual(seam.find_defects(vertices, faces, 0, 16.0), [])

    def test_a_far_vertex_is_a_step_in_the_building_not_a_slip(self):
        vertices, faces = box(14.0, 16.0)
        vertices = displace(vertices, 5, 0, 15.5)
        self.assertEqual(seam.find_defects(vertices, faces, 0, 16.0), [])

    def test_a_vertex_with_no_neighbour_on_the_seam_is_not_in_the_loop(self):
        # An interior vertex that merely happens to sit inside the cohort band.
        vertices, faces = box(14.0, 16.0)
        vertices = list(vertices) + [(15.94, 117.5, 2.5)]
        faces = list(faces) + [(0, 3, 8)]
        found = seam.find_defects(vertices, faces, 0, 16.0)
        self.assertEqual(found, [], "an unattached vertex was treated as seam")

    def test_a_fragmented_cohort_has_no_seam_to_repair_towards(self):
        # Not simply "a majority off the seam" -- with a modal seam the
        # majority IS the seam, so that case cannot arise. What can arise is a
        # cohort that splits three ways: half of it agrees, the rest scatters,
        # and there is no coordinate the scatter can honestly be pulled to.
        vertices, faces = box(14.0, 16.0)
        vertices = list(vertices) + [(16.0, 117.0, 2.0), (15.93, 118.0, 3.0)]
        faces = list(faces) + [(4, 8, 9)]
        for index in (6, 7):
            vertices = displace(vertices, index, 0, 15.96)
        # Cohort of six: three at 16.0, two at 15.96, one at 15.93.
        self.assertEqual(seam.find_defects(vertices, faces, 0, 16.0), [])

    def test_an_axis_without_a_mirror_modifier_has_no_seam(self):
        vertices, faces = box(14.0, 16.0)
        vertices = displace(vertices, 5, 0, 15.93)
        moved, repairs = seam.normalise(vertices, faces, mirror_axes=(),
                                        planes=())
        self.assertEqual(repairs, [])
        self.assertEqual(moved, vertices)

    def test_a_cohort_too_small_to_be_a_loop_is_skipped(self):
        # Two vertices cannot establish a seam coordinate. Repairing against
        # one of them would be a coin toss.
        vertices = [(16.0, 115.0, 0.0), (15.93, 115.0, 5.0), (14.0, 115.0, 0.0)]
        faces = [(0, 1, 2)]
        self.assertEqual(seam.find_defects(vertices, faces, 0, 16.0), [])


class RepairTests(unittest.TestCase):
    """The two instances actually present in the owner's file."""

    def test_the_west_house_vertex_is_pulled_back_onto_a_clean_seam(self):
        vertices, faces = box(14.0, 16.0)
        vertices = displace(vertices, 5, 0, 15.93)
        found = seam.find_defects(vertices, faces, 0, 16.0)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["vertex"], 5)
        self.assertAlmostEqual(found[0]["offset"], -0.07)
        self.assertAlmostEqual(found[0]["to"], 16.0)

    def test_the_006_vertex_is_pulled_onto_the_drifted_seam_not_the_plane(self):
        # The decisive case. The seam sits at 115.00169 and the defect is
        # 114.93169 -- exactly -0.07 relative to its own cohort. The repair
        # must land on 115.00169, NOT on the nominal 115.0, or it silently
        # un-drifts the object as a side effect of fixing one vertex.
        vertices, faces = box(110.1017, 115.0017)
        vertices = displace(vertices, 5, 0, 114.93169)
        found = seam.find_defects(vertices, faces, 0, 115.0)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["to"], 115.0017, places=4)
        self.assertNotAlmostEqual(found[0]["to"], 115.0, places=4)

    def test_the_repair_moves_one_vertex_on_one_axis_and_nothing_else(self):
        vertices, faces = box(14.0, 16.0)
        broken = displace(vertices, 5, 0, 15.93)
        moved, repairs = seam.normalise(broken, faces, mirror_axes=(0,),
                                        planes=(16.0,))
        self.assertEqual(len(repairs), 1)
        self.assertEqual(list(moved), list(vertices))
        for index, (before, after) in enumerate(zip(broken, moved)):
            if index != 5:
                self.assertEqual(before, after)
        self.assertEqual(broken[5][1:], moved[5][1:])

    def test_repairing_is_idempotent(self):
        vertices, faces = box(14.0, 16.0)
        broken = displace(vertices, 5, 0, 15.93)
        once, first = seam.normalise(broken, faces, (0,), (16.0,))
        twice, second = seam.normalise(once, faces, (0,), (16.0,))
        self.assertEqual(once, twice)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_strict_mode_makes_an_absent_repair_loud(self):
        vertices, faces = box(14.0, 16.0)
        with self.assertRaises(seam.SeamRefusal):
            seam.normalise(vertices, faces, (0,), (16.0,), strict=True)


class SeamCoordinateTests(unittest.TestCase):
    def test_the_mode_wins_not_the_mean(self):
        # A mean would be dragged by the very outlier being looked for.
        self.assertAlmostEqual(
            seam.seam_coordinate([16.0, 16.0, 16.0, 15.93]), 16.0)

    def test_a_cohort_that_agrees_on_nothing_has_no_seam(self):
        self.assertIsNone(seam.seam_coordinate([16.0, 15.9, 15.8, 15.7]))

    def test_coordinates_within_the_weld_tolerance_are_one_cluster(self):
        self.assertAlmostEqual(
            seam.seam_coordinate([16.0, 16.0002, 16.0004]), 16.0002, places=4)


if __name__ == "__main__":
    unittest.main()
