import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar.openings import PROFILES, build_openings
from house_grammar.recipe import BuildingRecipe, Course, Opening, Wing
from house_grammar.records import GrammarError


def wing(width=8.0, height=6.0, **kwargs):
    return Wing(id="front", lane_offset=0.0, width=width, depth=5.0,
                courses=(Course(kind="storey", height=height,
                                semantic="whitewash"),), **kwargs)


def recipe(*openings, **kwargs):
    return BuildingRecipe(id="test", version=1, wings=(wing(),), roof=(),
                          openings=openings, **kwargs)


def door(**kwargs):
    fields = dict(id="main", kind="door", wing="front", lane_offset=0.0,
                  width=1.15, height=2.25)
    fields.update(kwargs)
    return Opening(**fields)


def window(**kwargs):
    fields = dict(id="left", kind="window", wing="front", lane_offset=-2.0,
                  width=0.95, height=1.25, sill_z=1.15)
    fields.update(kwargs)
    return Opening(**fields)


def semantics(record):
    return set(record.face_materials)


def faces_of(record, semantic):
    return [face for face, name in zip(record.faces, record.face_materials)
            if name == semantic]


def extent(record, face, axis):
    values = [record.vertices[index][axis] for index in face]
    return (min(values), max(values))


class OpeningRecordTests(unittest.TestCase):
    def test_is_deterministic(self):
        source = recipe(door(), window())
        first = [record.fingerprint() for record in build_openings(source)]
        second = [record.fingerprint() for record in build_openings(source)]
        self.assertEqual(first, second)

    def test_one_record_per_opening_in_recipe_order(self):
        records = build_openings(recipe(window(), door()))
        self.assertEqual([record.role for record in records],
                         ["window:left", "door:main"])
        for record in records:
            self.assertEqual(record.parent_role, "body")

    def test_origin_is_the_opening_centre_on_the_street_face(self):
        record, = build_openings(recipe(window()))
        self.assertEqual(record.origin, (0.0, -2.0, 0.0))


class DoorTests(unittest.TestCase):
    def full_door(self):
        return door(lintel=True, drip=True, sill=True, shutters=True,
                    grille=True, pediment=True, panels=3, jamb=0.16)

    def test_every_member_contributes_its_own_semantic(self):
        record, = build_openings(recipe(self.full_door()))
        self.assertEqual(
            semantics(record),
            {"rough_limestone", "terracotta", "dark_wood", "wrought_iron"})

    def test_no_slab_spans_the_opening_behind_the_leaf(self):
        # The failure exterior.doorway() calls out: a solid rectangle behind
        # the leaf reads as a pasted-on rectangle instead of as depth.
        opening = self.full_door()
        record, = build_openings(recipe(opening))
        half = opening.width / 2.0
        leaf_back = max(vertex[0] for vertex in record.vertices)
        for face, semantic in zip(record.faces, record.face_materials):
            y_low, y_high = extent(record, face, 1)
            z_low, z_high = extent(record, face, 2)
            spans = (y_low <= -half + 1e-6 and y_high >= half - 1e-6
                     and z_low <= 1e-6 and z_high >= opening.height - 1e-6)
            if not spans:
                continue
            # Only the leaf itself may span the opening, and nothing may sit
            # deeper into the building than the leaf's own back face.
            self.assertEqual(semantic, "dark_wood")
            self.assertLessEqual(min(record.vertices[i][0] for i in face),
                                 leaf_back)

    def test_panels_add_leaf_geometry_inside_the_leaf_bounds(self):
        plain, = build_openings(recipe(door(panels=0)))
        panelled, = build_openings(recipe(door(panels=3)))
        self.assertGreater(len(faces_of(panelled, "dark_wood")),
                           len(faces_of(plain, "dark_wood")))
        _, (_, leaf_y, leaf_z) = plain.bounds()
        for face in faces_of(panelled, "dark_wood"):
            self.assertLessEqual(extent(panelled, face, 1)[1], leaf_y + 1e-9)
            self.assertLessEqual(extent(panelled, face, 2)[1], leaf_z + 1e-9)

    def test_a_door_has_no_pane(self):
        record, = build_openings(recipe(self.full_door()))
        self.assertNotIn("smoked_glass", semantics(record))


class WindowTests(unittest.TestCase):
    def test_carries_a_pane_a_frame_and_a_mullion(self):
        opening = window()
        record, = build_openings(recipe(opening))
        self.assertIn("smoked_glass", semantics(record))
        wood = faces_of(record, "dark_wood")
        self.assertTrue(wood, "the window has no wood frame")
        # The mullion is the one wood member narrower than it is tall.
        mullions = [face for face in wood
                    if extent(record, face, 1)[1] - extent(record, face, 1)[0] < 0.08
                    and extent(record, face, 2)[1] - extent(record, face, 2)[0]
                    > opening.height - 1e-6]
        self.assertTrue(mullions, "the pane has no mullion to break it up")

    def test_lit_is_metadata_and_the_pane_stays_smoked_glass(self):
        record, = build_openings(recipe(window(lit=True)))
        self.assertIs(record.metadata["lit"], True)
        self.assertTrue(faces_of(record, "smoked_glass"))


class ProfileTests(unittest.TestCase):
    def test_every_supported_profile_builds(self):
        for name in ("plain", "shop", "civic"):
            with self.subTest(profile=name):
                record, = build_openings(
                    recipe(window(profile=name, sill_z=1.4)))
                self.assertTrue(record.faces)
        self.assertEqual(set(PROFILES), {"plain", "shop", "civic"})

    def test_civic_gets_a_pediment_without_asking(self):
        plain, = build_openings(recipe(door(profile="plain")))
        civic, = build_openings(recipe(door(profile="civic")))
        self.assertGreater(civic.bounds()[1][2], plain.bounds()[1][2])

    def test_unknown_profile_names_itself(self):
        with self.assertRaisesRegex(GrammarError, "baroque"):
            build_openings(recipe(door(profile="baroque")))


class ValidationTests(unittest.TestCase):
    def test_opening_wider_than_its_wing_names_the_opening(self):
        with self.assertRaisesRegex(GrammarError, "main"):
            build_openings(recipe(door(width=9.0)))

    def test_members_past_the_wing_end_are_caught(self):
        # Fits by itself; its lintel and drip do not.
        with self.assertRaisesRegex(GrammarError, "main"):
            build_openings(recipe(door(lane_offset=3.4, width=1.15, drip=True)))

    def test_a_sill_below_ground_is_caught(self):
        with self.assertRaisesRegex(GrammarError, "below ground"):
            build_openings(recipe(window(sill_z=0.05)))

    def test_a_head_above_the_eave_is_caught(self):
        with self.assertRaisesRegex(GrammarError, "eave_z"):
            build_openings(recipe(window(sill_z=4.9, height=1.25)))


class MirrorTests(unittest.TestCase):
    def test_openings_are_never_mirrored(self):
        source = recipe(window(lane_offset=-2.5), window(id="right",
                                                         lane_offset=2.5),
                        mirror_axes=("Y",))
        records = build_openings(source)
        self.assertEqual(len(records), 2)
        negative = records[0]
        self.assertEqual(negative.origin[1], -2.5)
        self.assertEqual(negative.modifiers, ())


if __name__ == "__main__":
    unittest.main()
