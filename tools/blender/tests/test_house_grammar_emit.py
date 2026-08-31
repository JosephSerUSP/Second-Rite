"""The Blender emitter's contract with the house grammar's records.

The grammar itself is unit-tested without Blender; this suite covers the thin
layer that cannot be -- naming, parenting, transforms, material slots, the
modifier stack, and the two failure modes that would otherwise leave the
owner's file damaged. One Blender process runs `house_grammar_emit_blender.py`
and prints a JSON line; every test asserts against that.
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

PROBE = Path(__file__).resolve().parent / "house_grammar_emit_blender.py"


class HouseEmitterTests(unittest.TestCase):
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
                "the emitter probe produced no result:\n"
                + proc.stdout[-3000:] + "\n" + proc.stderr[-3000:])
        cls.probe = json.loads(line[len("PROBE "):])

    # -- shape -------------------------------------------------------------
    def test_one_object_per_record_under_one_root(self):
        self.assertEqual(self.probe["objects"],
                         ["STUDY_HOUSE_ROOT", "STUDY_HOUSE_body",
                          "STUDY_HOUSE_roof", "STUDY_HOUSE_window_w0"])
        for role, child in self.probe["children"].items():
            self.assertEqual(child["parent"], "STUDY_HOUSE_ROOT", role)

    def test_lane_position_goes_through_the_exterior_conversion(self):
        """The determinant -1 basis is handled here and nowhere else, so a root
        emitted at lane 3 on a 20 m lane must land at Blender Y 7."""
        self.assertAlmostEqual(self.probe["rootY"], 7.0, places=6)
        self.assertAlmostEqual(self.probe["plainRootY"], 2.5, places=6)

    def test_children_carry_a_clean_transform_and_no_parent_inverse(self):
        for role, child in self.probe["children"].items():
            self.assertEqual(child["scale"], [1.0, 1.0, 1.0], role)
            self.assertEqual(child["rotation"], [0.0, 0.0, 0.0], role)
            self.assertEqual(child["location"], child["origin"], role)
            # A keep-world inverse under an explicit local placement makes the
            # outliner look right while the object sits somewhere unrelated.
            self.assertTrue(child["parentInverseIdentity"], role)

    # -- materials ---------------------------------------------------------
    def test_material_index_per_face_matches_the_record_semantics(self):
        for role in ("body", "roof"):
            child = self.probe["children"][role]
            self.assertEqual(child["polygonSemantics"],
                             child["recordSemantics"], role)

    def test_a_lit_record_swaps_only_its_glass_for_an_emissive(self):
        self.assertEqual(self.probe["litWindowSemantics"],
                         ["sr_dark_wood", "sr_window_daylight"])

    # -- modifiers ---------------------------------------------------------
    def test_mirror_is_installed_editable_and_not_baked(self):
        roof = self.probe["children"]["roof"]
        self.assertEqual(roof["modifiers"], [{"type": "MIRROR", "axes": ["Y"]}])
        # Six faces: one box, the mirrored half still living in the stack
        # rather than in the mesh.
        self.assertEqual(roof["faceCount"], 6)
        self.assertEqual(self.probe["children"]["body"]["modifiers"], [])

    # -- normals -----------------------------------------------------------
    def test_normals_are_recalculated_outward(self):
        self.assertTrue(self.probe["children"]["body"]["normalsOutward"])
        self.assertTrue(self.probe["children"]["roof"]["normalsOutward"])
        self.assertTrue(self.probe["invertedNormalsFixed"])

    # -- provenance --------------------------------------------------------
    def test_root_stores_the_baseline_fingerprints(self):
        baseline = self.probe["provenance"]["baseline"]
        self.assertEqual(sorted(baseline), ["body", "roof", "window:w0"])
        self.assertEqual(sorted(self.probe["baselineRoles"]), sorted(baseline))

    # -- failure modes -----------------------------------------------------
    def test_a_name_collision_raises_before_anything_is_created(self):
        self.assertTrue(self.probe["collision"]["raised"])
        self.assertIn("already exist", self.probe["collision"]["message"])
        # Still exactly what the two earlier emissions made -- four for the
        # house, two for the inverted-winding check -- and nothing half-built.
        self.assertEqual(self.probe["collisionLeftCount"], 6)

    def test_a_malformed_record_rolls_the_whole_emission_back(self):
        """A half-built house in the owner's file is worse than a failure."""
        self.assertTrue(self.probe["rollback"]["raised"])
        self.assertEqual(self.probe["rollbackLeftNames"], [])
        self.assertEqual(self.probe["rollbackLeftCount"], 0)

    def test_the_emitter_never_saves(self):
        self.assertTrue(self.probe["savedNothing"])

    # -- diff --------------------------------------------------------------
    def test_diff_reports_identical_for_an_untouched_emission(self):
        for role, entry in self.probe["diffIdentical"].items():
            self.assertEqual(entry["status"], "identical", role)

    def test_diff_reports_a_moved_vertex_as_changed(self):
        body = self.probe["diffMoved"]["body"]
        self.assertEqual(body["status"], "changed")
        self.assertEqual(body["vertexDelta"], 0)
        self.assertEqual(self.probe["diffMoved"]["roof"]["status"], "identical")

    def test_diff_reports_counts_materials_and_absent_roles(self):
        grown = self.probe["diffGrown"]
        self.assertEqual(grown["body"]["status"], "changed")
        self.assertEqual(grown["body"]["vertexDelta"], 4)
        self.assertEqual(grown["body"]["faceDelta"], 4)
        self.assertEqual(grown["body"]["materialsAdded"], ["old_limestone"])
        self.assertEqual(grown["window:w0"]["status"], "missing")

    def test_diff_sees_a_hand_scaled_object_as_unclean(self):
        """The one edit the report exists to protect: never auto-fitted."""
        self.assertFalse(self.probe["diffAfterHandScale"]["transformClean"])


if __name__ == "__main__":
    unittest.main()
