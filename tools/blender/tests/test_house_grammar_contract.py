"""The guards on the house grammar's frozen contract.

These test `records.py` and `recipe.py` only -- the interface every builder is
written against. The builders have their own suites; what is asserted here is
the thing that would silently corrupt all three of them at once if it drifted:
the weld grid, the internal-face cancellation, the validation predicates, and
the fingerprint that the baseline diff is built on.

The internal-face rule is the load-bearing one. "One body mesh" is only true
if adding two abutting courses removes the face between them; if that ever
stops working the grammar still produces a plausible-looking record, and the
failure shows up as a shading artefact in a render weeks later.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar.records import (  # noqa: E402
    WELD, GrammarError, MeshBuilder, MeshRecord, ModifierSpec, face_area,
    face_normal, key, quantise, recentre, validate,
)
from house_grammar.recipe import (  # noqa: E402
    BuildingRecipe, Course, Opening, RoofSection, Wing,
)


def simple_courses():
    return (Course("plinth", 0.35, "rough_limestone"),
            Course("storey", 2.9, "whitewash", return_semantic="rough_limestone"),
            Course("cornice", 0.18, "rough_limestone", inset=-0.06))


def simple_wing(**kw):
    params = dict(id="main", lane_offset=0.0, width=6.0, depth=4.2,
                  courses=simple_courses())
    params.update(kw)
    return Wing(**params)


class WeldTests(unittest.TestCase):
    def test_quantise_snaps_to_the_grid_and_normalises_negative_zero(self):
        self.assertEqual(quantise(-0.0), 0.0)
        self.assertEqual(quantise(1.0 + WELD / 4.0), 1.0)
        self.assertNotEqual(quantise(1.0 + WELD * 2.0), 1.0)

    def test_coincident_vertices_weld_to_one_index(self):
        builder = MeshBuilder("weld")
        first = builder.vertex((1.0, 2.0, 3.0))
        again = builder.vertex((1.0 + WELD / 8.0, 2.0, 3.0))
        self.assertEqual(first, again)


class InternalFaceTests(unittest.TestCase):
    def test_two_abutting_boxes_lose_the_shared_face(self):
        builder = MeshBuilder("fuse")
        builder.add_box((0, 0, 0), (1, 1, 1), "whitewash")
        builder.add_box((1, 0, 0), (2, 1, 1), "whitewash")
        record = builder.record("body")
        # Twelve faces were offered; the shared pair cancelled.
        self.assertEqual(len(record.faces), 10)
        self.assertEqual(record.bounds(), ((0.0, 0.0, 0.0), (2.0, 1.0, 1.0)))

    def test_the_fused_solid_is_closed(self):
        builder = MeshBuilder("closed")
        builder.add_box((0, 0, 0), (1, 1, 1), "whitewash")
        builder.add_box((1, 0, 0), (2, 1, 1), "whitewash")
        record = builder.record("body")
        edges = {}
        for face in record.faces:
            for index in range(len(face)):
                pair = frozenset((face[index], face[(index + 1) % len(face)]))
                edges[pair] = edges.get(pair, 0) + 1
        self.assertTrue(all(count == 2 for count in edges.values()),
                        "a closed solid shares every edge between exactly two faces")

    def test_cancellation_survives_the_vertex_rebuild(self):
        # A vertex used only by a cancelled face must not survive as an orphan;
        # validate() would reject it, so this asserts the compaction as well.
        builder = MeshBuilder("compact")
        builder.add_box((0, 0, 0), (1, 1, 1), "whitewash", faces=("+x",))
        builder.add_box((0, 0, 0), (1, 1, 1), "whitewash", faces=("+x",))
        self.assertTrue(builder.is_empty())

    def test_add_box_rejects_a_degenerate_box(self):
        builder = MeshBuilder("flat")
        with self.assertRaises(GrammarError):
            builder.add_box((0, 0, 0), (1, 1, 0), "whitewash")


class ValidationTests(unittest.TestCase):
    def record(self, **kw):
        params = dict(role="body", name="r", origin=(0.0, 0.0, 0.0),
                      vertices=((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
                      faces=((0, 1, 2, 3),), face_materials=("whitewash",))
        params.update(kw)
        return MeshRecord(**params)

    def test_accepts_a_well_formed_record(self):
        self.assertIs(validate(self.record()).semantic, "body")

    def test_rejects_an_unknown_role(self):
        with self.assertRaisesRegex(GrammarError, "unknown role"):
            validate(self.record(role="chimney"))

    def test_rejects_an_opening_role_without_an_id(self):
        with self.assertRaisesRegex(GrammarError, "needs an id"):
            validate(self.record(role="door"))

    def test_rejects_a_body_role_carrying_an_id(self):
        with self.assertRaisesRegex(GrammarError, "takes no id"):
            validate(self.record(role="body:front"))

    def test_rejects_a_material_count_mismatch(self):
        with self.assertRaisesRegex(GrammarError, "face materials"):
            validate(self.record(face_materials=()))

    def test_rejects_an_out_of_range_index(self):
        with self.assertRaisesRegex(GrammarError, "indexes vertex"):
            validate(self.record(faces=((0, 1, 9),), face_materials=("whitewash",)))

    def test_rejects_a_repeated_vertex_in_one_face(self):
        with self.assertRaisesRegex(GrammarError, "repeats a vertex"):
            validate(self.record(faces=((0, 1, 1, 2),), face_materials=("whitewash",)))

    def test_rejects_a_degenerate_face(self):
        with self.assertRaisesRegex(GrammarError, "degenerate"):
            validate(self.record(
                vertices=((0, 0, 0), (1, 0, 0), (2, 0, 0)),
                faces=((0, 1, 2),), face_materials=("whitewash",)))

    def test_rejects_a_surviving_internal_face(self):
        with self.assertRaisesRegex(GrammarError, "internal face"):
            validate(self.record(faces=((0, 1, 2, 3), (3, 2, 1, 0)),
                                 face_materials=("whitewash", "whitewash")))

    def test_rejects_an_orphaned_vertex(self):
        with self.assertRaisesRegex(GrammarError, "unused"):
            validate(self.record(
                vertices=((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (5, 5, 5))))

    def test_opening_roles_split_into_semantic_and_id(self):
        record = validate(self.record(role="window:front_upper_02"))
        self.assertEqual(record.semantic, "window")
        self.assertEqual(record.opening_id, "front_upper_02")


class FingerprintTests(unittest.TestCase):
    def build(self, offset=0.0):
        builder = MeshBuilder("fp")
        builder.add_box((offset, 0, 0), (offset + 1, 1, 1), "whitewash")
        return builder.record("body")

    def test_is_stable_across_rebuilds(self):
        self.assertEqual(self.build().fingerprint(), self.build().fingerprint())

    def test_changes_when_the_geometry_moves(self):
        self.assertNotEqual(self.build().fingerprint(), self.build(0.5).fingerprint())

    def test_changes_when_only_a_material_changes(self):
        first = self.build()
        second = MeshRecord(**{**first.__dict__,
                               "face_materials": ("azulejo",) * len(first.faces)})
        self.assertNotEqual(first.fingerprint(), second.fingerprint())

    def test_changes_when_only_a_modifier_changes(self):
        first = self.build()
        second = MeshRecord(**{**first.__dict__,
                               "modifiers": (ModifierSpec("MIRROR", axes=("Y",)),)})
        self.assertNotEqual(first.fingerprint(), second.fingerprint())


class MaterialRegionTests(unittest.TestCase):
    def test_a_region_survives_retriangulation(self):
        # Conformance compares regions, not indices, precisely so that a quad
        # rebuilt as two triangles still matches. If this ever fails, the
        # conformance gate has quietly become an ordered-index gate again.
        quad = MeshRecord(role="body", name="q", origin=(0, 0, 0),
                          vertices=((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)),
                          faces=((0, 1, 2, 3),), face_materials=("whitewash",))
        split = MeshRecord(role="body", name="s", origin=(0, 0, 0),
                           vertices=((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)),
                           faces=((0, 1, 2), (0, 2, 3)),
                           face_materials=("whitewash", "whitewash"))
        self.assertEqual(set(quad.material_regions()), set(split.material_regions()))
        self.assertNotEqual(quad.material_regions(), split.material_regions())

    def test_regions_are_reported_in_world_space(self):
        builder = MeshBuilder("world")
        builder.add_box((0, 0, 0), (1, 1, 1), "whitewash")
        here = builder.record("body", origin=(0, 0, 0))
        moved = recentre(here, (5.0, 0.0, 0.0))
        self.assertEqual(here.material_regions(), moved.material_regions())
        self.assertEqual(moved.origin, (5.0, 0.0, 0.0))
        self.assertEqual(moved.bounds()[0][0], -5.0)


class GeometryHelperTests(unittest.TestCase):
    def test_area_of_a_unit_square(self):
        self.assertAlmostEqual(
            face_area(((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), (0, 1, 2, 3)),
            1.0)

    def test_normal_of_a_ccw_square_points_up(self):
        normal = face_normal(((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
                             (0, 1, 2, 3))
        self.assertAlmostEqual(normal[2], 1.0)

    def test_a_collapsed_face_has_no_normal_rather_than_raising(self):
        self.assertEqual(face_normal(((0, 0, 0), (1, 0, 0), (2, 0, 0)), (0, 1, 2)),
                         (0.0, 0.0, 0.0))


class RecipeSchemaTests(unittest.TestCase):
    def test_a_wing_reports_its_eave_and_top(self):
        wing = simple_wing()
        # The gable cap sits above the eave, so the eave is the top of the
        # last non-cap course and the two differ only when a cap is present.
        self.assertAlmostEqual(wing.eave_z, 3.43)
        self.assertAlmostEqual(wing.top_z, 3.43)
        capped = simple_wing(courses=simple_courses() + (
            Course("gable_cap", 1.6, "whitewash"),))
        self.assertAlmostEqual(capped.eave_z, 3.43)
        self.assertAlmostEqual(capped.top_z, 5.03)

    def test_a_wing_reports_its_spans(self):
        wing = simple_wing(lane_offset=2.0, setback=0.5)
        self.assertEqual(wing.y_span(), (-1.0, 5.0))
        self.assertEqual(wing.x_span(), (0.5, 4.7))

    def test_a_course_rejects_an_unknown_kind_and_semantic(self):
        with self.assertRaisesRegex(GrammarError, "course kind"):
            Course("buttress", 1.0, "whitewash")
        with self.assertRaisesRegex(GrammarError, "material semantic"):
            Course("storey", 1.0, "marble")

    def test_a_wing_needs_courses_and_positive_extents(self):
        with self.assertRaisesRegex(GrammarError, "no courses"):
            simple_wing(courses=())
        with self.assertRaisesRegex(GrammarError, "must be positive"):
            simple_wing(width=0.0)

    def test_numbers_must_be_finite(self):
        with self.assertRaisesRegex(GrammarError, "finite"):
            simple_wing(setback=float("nan"))
        with self.assertRaisesRegex(GrammarError, "finite"):
            simple_wing(setback=float("inf"))

    def test_roof_rejects_unknown_profiles_axes_and_fractions(self):
        with self.assertRaisesRegex(GrammarError, "roof profile"):
            RoofSection(wing="main", profile="mansard")
        with self.assertRaisesRegex(GrammarError, "ridge axis"):
            RoofSection(wing="main", ridge_axis="Z")
        with self.assertRaisesRegex(GrammarError, "hip_fraction"):
            RoofSection(wing="main", profile="half_hip", hip_fraction=1.0)

    def test_a_door_may_not_carry_a_sill_height(self):
        with self.assertRaisesRegex(GrammarError, "threshold"):
            Opening(id="d1", kind="door", wing="main", lane_offset=0.0,
                    width=1.15, height=2.25, sill_z=0.4)

    def test_an_opening_id_may_not_contain_the_role_separator(self):
        with self.assertRaisesRegex(GrammarError, "free of"):
            Opening(id="front:door", kind="door", wing="main", lane_offset=0.0,
                    width=1.15, height=2.25)

    def test_an_opening_reports_its_role_and_span(self):
        opening = Opening(id="d1", kind="door", wing="main", lane_offset=1.0,
                          width=1.2, height=2.25)
        self.assertEqual(opening.role, "door:d1")
        self.assertEqual(opening.y_span(), (0.4, 1.6))


class RecipeCoherenceTests(unittest.TestCase):
    def recipe(self, **kw):
        params = dict(id="test_house", version=1, wings=(simple_wing(),),
                      roof=(RoofSection(wing="main"),))
        params.update(kw)
        return BuildingRecipe(**params)

    def test_accepts_a_coherent_recipe(self):
        self.assertEqual(self.recipe().wing("main").id, "main")
        self.assertEqual(self.recipe().roof_section("main").profile, "gable")
        self.assertIsNone(self.recipe(roof=()).roof_section("main"))

    def test_rejects_duplicate_wing_ids(self):
        with self.assertRaisesRegex(GrammarError, "duplicate wing ids"):
            self.recipe(wings=(simple_wing(), simple_wing()))

    def test_rejects_a_roof_over_an_unknown_wing(self):
        with self.assertRaisesRegex(GrammarError, "unknown wing"):
            self.recipe(roof=(RoofSection(wing="annex"),))

    def test_rejects_two_roof_sections_over_one_wing(self):
        with self.assertRaisesRegex(GrammarError, "two roof sections"):
            self.recipe(roof=(RoofSection(wing="main"),
                              RoofSection(wing="main", profile="hip")))

    def test_rejects_an_opening_on_an_unknown_wing(self):
        with self.assertRaisesRegex(GrammarError, "unknown wing"):
            self.recipe(openings=(Opening(id="d1", kind="door", wing="annex",
                                          lane_offset=0.0, width=1.1,
                                          height=2.25),))

    def test_rejects_duplicate_opening_ids(self):
        door = Opening(id="d1", kind="door", wing="main", lane_offset=0.0,
                       width=1.1, height=2.25)
        with self.assertRaisesRegex(GrammarError, "duplicate opening ids"):
            self.recipe(openings=(door, door))

    def test_an_axis_is_mirrored_or_baked_but_never_both(self):
        # The distinction is the whole point of declaring them: it is what lets
        # the symmetry test tell an intentional asymmetry from a bug.
        with self.assertRaisesRegex(GrammarError, "one or the other"):
            self.recipe(mirror_axes=("Y",), baked_axes=("Y",))
        self.assertEqual(self.recipe(mirror_axes=("Y",)).mirror_axes, ("Y",))
        self.assertEqual(self.recipe(baked_axes=("Y",)).baked_axes, ("Y",))

    def test_rejects_an_unknown_axis_and_a_zero_version(self):
        with self.assertRaisesRegex(GrammarError, "unknown axis"):
            self.recipe(mirror_axes=("W",))
        with self.assertRaisesRegex(GrammarError, "version"):
            self.recipe(version=0)


if __name__ == "__main__":
    unittest.main()
