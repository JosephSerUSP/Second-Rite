"""The St. Maria interior grammar's axes, and the guards on them.

The shell could express exactly one shape -- a box with one pierced back wall
-- and every interior authored against it came out looking like the same room
with different props. These are the axes that were added to break that, and
the two guards that keep them from breaking the vocabulary instead.

One Blender process runs `interior_grammar_probe.py` and prints a JSON line;
every test here asserts against that. Spawning Blender once keeps the suite
fast enough to stay in the default run.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLENDER_TOOLS = ROOT / "tools" / "blender"
sys.path.insert(0, str(BLENDER_TOOLS))

import build_synthetic_environment  # noqa: E402

PROBE = Path(__file__).resolve().parent / "interior_grammar_probe.py"


class InteriorGrammarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blender = build_synthetic_environment.blender_executable()
        proc = subprocess.run(
            [str(blender), "--background", "--factory-startup",
             "--python", str(PROBE)],
            capture_output=True, text=True, timeout=600,
        )
        line = next((l for l in proc.stdout.splitlines()
                     if l.startswith("PROBE ")), None)
        if line is None:
            raise AssertionError(
                "the grammar probe produced no result:\n"
                + proc.stdout[-3000:] + "\n" + proc.stderr[-3000:])
        cls.probe = json.loads(line[len("PROBE "):])

    # -- projection --------------------------------------------------------
    def test_native_y_at_inverts_floor_edge_x(self):
        """The two helpers have to agree, or every frame check built on
        `native_y_at` is measuring a different camera than the stager."""
        self.assertAlmostEqual(self.probe["projectionRoundTrip"], 0.0,
                               places=4)

    # -- the axes ----------------------------------------------------------
    def test_plain_back_wall_is_one_plane(self):
        self.assertEqual(len(self.probe["plainBackWallPlanes"]), 1)

    def test_alcove_steps_the_wall_back_by_its_depth(self):
        planes = self.probe["alcoveBackWallPlanes"]
        self.assertEqual(len(planes), 2)
        self.assertAlmostEqual(self.probe["alcoveDepth"], 1.4, places=3)

    def test_alcove_builds_its_own_floor_ceiling_and_returns(self):
        self.assertIn("alcove_0", self.probe["alcoveParts"])
        self.assertIn("alcove_0_return", self.probe["alcoveParts"])

    def test_alcove_gets_a_header_across_its_mouth(self):
        """Without one the wall just moves back, which from a level lens 18m
        away is nearly invisible -- the recess reads as a bay, not a niche.
        This is what the first version of the axis got wrong."""
        self.assertTrue(self.probe["alcoveHasHeader"])

    def test_side_wall_opening_segments_the_wall(self):
        self.assertEqual(self.probe["sideWallSolidParts"], 1)
        self.assertGreater(self.probe["sideWallPiercedParts"],
                           self.probe["sideWallSolidParts"])

    def test_foreground_sits_between_the_camera_and_the_room(self):
        self.assertTrue(self.probe["foregroundIsInFront"])

    # -- behaviour preservation -------------------------------------------
    def test_empty_axis_arguments_change_nothing(self):
        """`back_wall(openings=X)` and `back_wall(openings=X, alcoves=[])`
        must be the same wall. Every map on main takes the first form."""
        self.assertTrue(self.probe["emptyArgsAreIdentical"])

    # -- the guards --------------------------------------------------------
    def test_raised_platform_is_allowed(self):
        self.assertTrue(self.probe["platformRaised"]["accepted"])

    def test_shallow_dip_is_allowed(self):
        self.assertTrue(self.probe["platformShallowDip"]["accepted"])

    def test_pit_past_the_character_floor_limit_is_refused(self):
        case = self.probe["platformDeepPit"]
        self.assertFalse(case["accepted"])
        self.assertIn("character floor limit", case["message"])

    def test_narrow_post_and_shallow_beam_are_allowed(self):
        """The guard measures COVERAGE, not width. A beam right across the top
        of frame is a real device and must not be mistaken for a proscenium."""
        self.assertTrue(self.probe["foregroundNarrowPost"]["accepted"])
        self.assertTrue(self.probe["foregroundShallowBeam"]["accepted"])

    def test_foreground_budget_is_cumulative(self):
        """Members that each pass on their own must not be able to close the
        frame down between them. The first version guarded per call, and a
        post plus a beam did exactly that."""
        case = self.probe["foregroundCumulative"]
        self.assertFalse(case["accepted"])
        self.assertIn("already spent", case["message"])

    def test_occluder_over_the_composition_is_refused(self):
        for label in ("foregroundMiddleSlab", "foregroundProscenium"):
            case = self.probe[label]
            self.assertFalse(case["accepted"], label)
            self.assertIn("proscenium", case["message"], label)

    def test_overlapping_alcoves_are_refused(self):
        self.assertFalse(self.probe["alcoveOverlapRefused"]["accepted"])

    def test_opening_straddling_an_alcove_edge_is_refused(self):
        case = self.probe["alcoveStraddlingOpeningRefused"]
        self.assertFalse(case["accepted"])
        self.assertIn("straddles", case["message"])


if __name__ == "__main__":
    unittest.main()
