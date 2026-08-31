"""The camera predicates, pinned to independently measured constants.

`house_grammar.staging` reimplements the town camera's projection because the
scene-side copy in `interior.py` imports bpy and the grammar must run in the
ordinary unit gate. A reimplementation is only safe if something outside it
says what the right answers are, so every number asserted here was measured
first and written into `exterior.py` and the camera fixture's own
`thestraComposition` block, long before this module existed:

    a 1.75 m walker reads 48 px with its feet on scanline 128 and head on 80
    the ground plane leaves the frame at X = -12.01
    dock cover heights are 1.09 m at X = -11, 0.64 m at X = -8, 0.03 m at X = -4

If the projection here ever drifts, one of those stops matching. That is the
whole point of the file.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar import staging  # noqa: E402
from house_grammar.records import MeshBuilder  # noqa: E402


def slab(name, low, high, semantic="whitewash", role="body"):
    builder = MeshBuilder(name)
    builder.add_box(low, high, semantic)
    return builder.record(role)


class ProjectionOracleTests(unittest.TestCase):
    """The four constants that were measured before this module existed."""

    def setUp(self):
        self.camera = staging.camera_record()

    def test_a_walker_reads_forty_eight_pixels_at_the_action_plane(self):
        pixels = staging.WALKER_HEIGHT_M * staging.pixels_per_metre_at(0.0, self.camera)
        self.assertAlmostEqual(pixels, 48.0, places=6)

    def test_the_walker_stands_on_scanline_128_with_its_head_on_80(self):
        self.assertAlmostEqual(staging.native_y_at(0.0, 0.0, self.camera), 128.0, places=6)
        self.assertAlmostEqual(
            staging.native_y_at(0.0, staging.WALKER_HEIGHT_M, self.camera), 80.0, places=6)

    def test_the_ground_leaves_the_frame_at_minus_twelve(self):
        self.assertLess(abs(staging.ground_exit_x(self.camera) - (-12.01)), 0.01)

    def test_dock_cover_heights_match_the_documented_falloff(self):
        for x, expected in ((-11.0, 1.09), (-8.0, 0.64), (-4.0, 0.03)):
            self.assertAlmostEqual(staging.dock_cover_height(x, self.camera),
                                   expected, places=2,
                                   msg=f"dock cover height at X={x}")

    def test_the_fixture_agrees_with_its_own_composition_block(self):
        composition = self.camera["thestraComposition"]
        self.assertEqual(composition["solvedDistance"], -self.camera["eye"]["x"])
        self.assertEqual(composition["horizonY"], self.camera["viewportCenterY"])
        self.assertAlmostEqual(
            staging.pixels_per_metre_at(0.0, self.camera),
            composition["pixelsPerWorldUnit"], places=6)

    def test_a_point_at_or_behind_the_camera_raises(self):
        with self.assertRaisesRegex(ValueError, "behind the camera"):
            staging.native_y_at(self.camera["eye"]["x"], 0.0, self.camera)


class PlacementTests(unittest.TestCase):
    """The lane conversion -- the trap that is invisible in every topology test."""

    def test_screen_right_is_negative_y(self):
        # A building one metre east along the lane must land one metre LOWER in
        # Blender Y. Getting this backwards mirrors the whole street and no
        # topology assertion can see it (issue #935).
        record = slab("w", (0, -1, 0), (4, 1, 3))
        west = staging.place(record, back_x=9.0, lane_y=0.0, lane_centre=10.0)
        east = staging.place(record, back_x=9.0, lane_y=1.0, lane_centre=10.0)
        self.assertAlmostEqual(east[0][1], west[0][1] - 1.0)
        self.assertAlmostEqual(east[1][1], west[1][1] - 1.0)

    def test_depth_offsets_from_the_terrace_line(self):
        record = slab("w", (0, -1, 0), (4, 1, 3))
        (x0, _, z0), (x1, _, z1) = staging.place(record, back_x=9.0, lane_y=0.0,
                                                 lane_centre=10.0)
        self.assertAlmostEqual(x0, 9.0)
        self.assertAlmostEqual(x1, 13.0)
        self.assertAlmostEqual(z0, 0.0)
        self.assertAlmostEqual(z1, 3.0)

    def test_the_local_plus_y_extent_maps_to_the_lower_scene_y(self):
        # Asymmetric on purpose: a symmetric box cannot catch a flipped axis.
        record = slab("w", (0, 0, 0), (4, 3, 3))
        (_, y0, _), (_, y1, _) = staging.place(record, back_x=9.0, lane_y=0.0,
                                               lane_centre=10.0)
        self.assertAlmostEqual(y1, 10.0)
        self.assertAlmostEqual(y0, 7.0)


class ReadableSizeTests(unittest.TestCase):
    def test_a_building_is_measured_against_a_person_at_the_same_depth(self):
        record = slab("house", (0, -3, 0), (4, 3, 6))
        size = staging.readable_size(record, back_x=9.0, lane_y=0.0, lane_centre=10.0)
        self.assertGreater(size["heightPx"], 0.0)
        self.assertGreater(size["walkerPx"], 0.0)
        # At the far terrace line the whole 6 m house reads smaller than four
        # walkers would, which is what "rooflines are out of frame" costs.
        self.assertAlmostEqual(size["heightPx"] / size["walkerPx"],
                               6.0 / staging.WALKER_HEIGHT_M, places=2)

    def test_the_same_building_reads_larger_nearer_the_lens(self):
        record = slab("house", (0, -3, 0), (4, 3, 6))
        far = staging.readable_size(record, back_x=9.0, lane_y=0.0, lane_centre=10.0)
        near = staging.readable_size(record, back_x=-6.0, lane_y=0.0, lane_centre=10.0)
        self.assertGreater(near["heightPx"], far["heightPx"])
        self.assertGreater(near["walkerPx"], far["walkerPx"])


class OccluderRuleTests(unittest.TestCase):
    """Tall or continuous, never both."""

    def classify(self, low, high, back_x=-8.0):
        record = slab("near", low, high)
        return staging.classify_occluder(record, back_x=back_x, lane_y=0.0,
                                         lane_centre=0.0)

    def test_a_pole_is_allowed(self):
        verdict = self.classify((0, -0.12, 0), (0.4, 0.12, 3.0))
        self.assertEqual(verdict["shape"], "pole")

    def test_a_low_skirt_is_allowed(self):
        verdict = self.classify((0, -4.0, 0), (0.5, 4.0, 0.55))
        self.assertEqual(verdict["shape"], "skirt")

    def test_a_board_that_swallows_the_character_is_rejected(self):
        verdict = self.classify((0, -4.0, 0), (0.5, 4.0, 4.0))
        self.assertEqual(verdict["shape"], "BOARD")

    def test_something_incidental_is_not_reported_at_all(self):
        self.assertIsNone(self.classify((0, -0.1, 0), (0.2, 0.1, 0.3)))

    def test_boards_is_the_gate_and_it_names_the_offender(self):
        good = slab("pole", (0, -0.12, 0), (0.4, 0.12, 3.0))
        bad = slab("hoarding", (0, -4.0, 0), (0.5, 4.0, 4.0))
        self.assertEqual(
            staging.boards([good], back_x=-8.0, lane_y=0.0, lane_centre=0.0), [])
        found = staging.boards([good, bad], back_x=-8.0, lane_y=0.0, lane_centre=0.0)
        self.assertEqual([row["name"] for row in found], ["hoarding"])

    def test_a_far_building_is_not_an_occluder_at_all(self):
        # The same mass at the terrace line covers the character and spans the
        # frame, so the shape test alone would call it a BOARD. It is framing:
        # the player walks in FRONT of it. Foreground is what you pass behind,
        # which makes this a depth test, not a shape test.
        self.assertIsNone(self.classify((0, -4.0, 0), (0.5, 4.0, 4.0), back_x=9.0))

    def test_the_gate_ignores_the_building_body_behind_the_action_plane(self):
        body = slab("body", (0, -6.0, 0), (4.0, 6.0, 6.0))
        self.assertEqual(
            staging.boards([body], back_x=9.0, lane_y=0.0, lane_centre=0.0), [])


class DockCoverageTests(unittest.TestCase):
    def test_coverage_is_reported_with_a_readable_size(self):
        # The pair is the metric. A wall that covers the band and reads as
        # nothing must still be visible as a poor result, which it only is if
        # the size travels with the coverage.
        wall = slab("wall", (0, -6.0, 0), (0.4, 6.0, 1.4))
        result = staging.dock_coverage([wall], back_x=-9.0, lane_y=0.0,
                                       lane_centre=0.0)
        self.assertGreater(result["coverage"], 0.5)
        self.assertIn("readable", result)
        self.assertGreater(result["readable"]["walkerPx"], 0.0)

    def test_a_piece_too_short_to_reach_the_menu_covers_nothing(self):
        # At X = -9 the band needs about 0.8 m; a 0.3 m kerb cannot reach it.
        kerb = slab("kerb", (0, -6.0, 0), (0.4, 6.0, 0.3))
        result = staging.dock_coverage([kerb], back_x=-9.0, lane_y=0.0,
                                       lane_centre=0.0)
        self.assertEqual(result["coverage"], 0.0)

    def test_no_records_covers_nothing_rather_than_raising(self):
        self.assertEqual(
            staging.dock_coverage([], back_x=-9.0, lane_y=0.0,
                                  lane_centre=0.0)["coverage"], 0.0)


if __name__ == "__main__":
    unittest.main()
