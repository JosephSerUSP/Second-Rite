"""The seam between the three builders, which none of them owns.

Each builder has its own suite and each passes in isolation. What is asserted
here is the contract BETWEEN them: that a recipe resolves to exactly one body,
one roof and one record per opening, in a fixed order; that the symmetry
declaration is honoured the same way by all three; and that a building from the
library survives the camera predicates.

The symmetry case is the one worth having. A mirrored body, a mirrored roof and
an UNMIRRORED set of openings is a combination no single builder can get wrong
on its own and no single builder can check.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar import library, staging  # noqa: E402
from house_grammar.recipe import (  # noqa: E402
    BuildingRecipe, Course, Opening, RoofSection, Wing, build,
)
from house_grammar.records import validate  # noqa: E402


def symmetric_recipe(**kw):
    """A plain hall, symmetric about the lane centre, with one off-centre door."""
    courses = (Course("plinth", 0.35, "rough_limestone"),
               Course("storey", 3.2, "whitewash",
                      return_semantic="rough_limestone"),
               Course("cornice", 0.2, "rough_limestone", inset=-0.07))
    params = dict(
        id="hall", version=1,
        wings=(Wing(id="main", lane_offset=0.0, width=8.0, depth=5.0,
                    courses=courses),),
        roof=(RoofSection(wing="main", profile="gable", ridge_axis="Y",
                          rise=1.6),),
        openings=(Opening(id="side_door", kind="door", wing="main",
                          lane_offset=-2.4, width=1.1, height=2.3),),
    )
    params.update(kw)
    return BuildingRecipe(**params)


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.recipe = library.narrow_townhouse()
        self.records = build(self.recipe)

    def test_one_body_one_roof_one_record_per_opening(self):
        roles = [record.role for record in self.records]
        self.assertEqual(roles[0], "body")
        self.assertEqual(roles[1], "roof")
        self.assertEqual(roles[2:],
                         [opening.role for opening in self.recipe.openings])
        self.assertEqual(len(set(roles)), len(roles))

    def test_every_record_validates_and_parents_correctly(self):
        for record in self.records:
            validate(record)
        self.assertIsNone(self.records[0].parent_role)
        for record in self.records[1:]:
            self.assertEqual(record.parent_role, "body")

    def test_the_whole_build_is_deterministic(self):
        again = build(library.narrow_townhouse())
        self.assertEqual([record.fingerprint() for record in self.records],
                         [record.fingerprint() for record in again])

    def test_a_roofless_recipe_emits_no_roof_record(self):
        records = build(symmetric_recipe(roof=()))
        self.assertEqual([record.semantic for record in records],
                         ["body", "door"])

    def test_every_registry_entry_builds(self):
        # The registry is what a study or the bridge enumerates, so an entry
        # that does not build is a broken menu item rather than a dead function.
        for name, factory in library.REGISTRY.items():
            with self.subTest(recipe=name):
                self.assertTrue(build(factory()))


class SymmetryDeclarationTests(unittest.TestCase):
    """Mirrored, baked, and the openings that are neither."""

    def mirrored(self):
        return build(symmetric_recipe(mirror_axes=("Y",)))

    def baked(self):
        return build(symmetric_recipe(baked_axes=("Y",)))

    def test_a_mirrored_recipe_emits_only_the_fundamental_domain(self):
        for record in self.mirrored():
            if record.semantic in ("body", "roof"):
                with self.subTest(role=record.role):
                    self.assertGreaterEqual(record.bounds()[0][1], -1e-9)

    def test_a_mirrored_body_and_roof_carry_an_editable_mirror(self):
        for record in self.mirrored():
            if record.semantic in ("body", "roof"):
                with self.subTest(role=record.role):
                    kinds = [(modifier.kind, modifier.axes)
                             for modifier in record.modifiers]
                    self.assertIn(("MIRROR", ("Y",)), kinds)

    def test_openings_are_never_mirrored_even_under_a_mirrored_recipe(self):
        # A mirror would MOVE a door the runtime anchors by lane position, so
        # an off-centre door under a symmetric facade must survive at its own
        # negative lane offset with no modifier attached.
        openings = [record for record in self.mirrored()
                    if record.semantic in ("door", "window")]
        self.assertEqual(len(openings), 1)
        self.assertEqual(openings[0].modifiers, ())
        self.assertLess(openings[0].origin[1], 0.0)

    def test_a_baked_axis_emits_both_halves_and_no_modifier(self):
        for record in self.baked():
            if record.semantic in ("body", "roof"):
                with self.subTest(role=record.role):
                    self.assertLess(record.bounds()[0][1], -1e-9)
                    self.assertEqual(record.modifiers, ())

    def test_the_library_townhouse_bakes_rather_than_mirrors(self):
        recipe = library.narrow_townhouse()
        self.assertEqual(recipe.baked_axes, ("Y",))
        self.assertEqual(recipe.mirror_axes, ())
        for record in build(recipe):
            self.assertEqual(record.modifiers, ())


class StagedBuildingTests(unittest.TestCase):
    """The camera predicates applied to a real generated building."""

    def setUp(self):
        self.records = build(library.narrow_townhouse())

    def test_the_townhouse_breaks_no_occluder_rule_at_the_terrace_line(self):
        self.assertEqual(
            staging.boards(self.records, back_x=9.0, lane_y=0.0, lane_centre=0.0),
            [])

    def test_the_body_reads_beside_a_person_at_the_same_depth(self):
        body = self.records[0]
        size = staging.readable_size(body, back_x=9.0, lane_y=0.0, lane_centre=0.0)
        self.assertGreater(size["walkerPx"], 0.0)
        # Narrow is the point of this typology: it must not span the frame, or
        # it reads as part of a terrace rather than as its own building.
        self.assertLess(size["widthFrames"], 0.5)

    def test_pulling_the_building_forward_makes_it_an_occluder(self):
        # A negative control on the gate itself. If nothing can ever be
        # reported as a BOARD, an empty boards() proves nothing about the
        # building -- it only proves the predicate is blind.
        found = staging.boards(self.records, back_x=-8.0, lane_y=0.0,
                               lane_centre=0.0)
        self.assertTrue(found, "the occluder gate reports nothing even at X=-8")
        self.assertEqual(found[0]["shape"], "BOARD")


if __name__ == "__main__":
    unittest.main()
