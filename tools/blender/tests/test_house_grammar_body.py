import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar.body import build_body
from house_grammar.recipe import BuildingRecipe, Course, Opening, RoofSection, Wing
from house_grammar.records import GrammarError


def courses(**overrides):
    """A plain St. Maria street wall: stone plinth, whitewash, projected cornice."""
    height = overrides.get("storey", 3.2)
    return (
        Course("plinth", 0.35, "rough_limestone", inset=-0.06),
        Course("storey", height, "whitewash", return_semantic="rough_limestone"),
        Course("cornice", 0.28, "old_limestone", inset=-0.22),
    )


def one_wing(**overrides):
    return BuildingRecipe(
        id="test_house", version=1,
        wings=(Wing("main", 0.0, 6.0, 4.0, courses=courses(**overrides)),),
        roof=(),
        **{k: v for k, v in overrides.items() if k not in ("storey",)},
    )


def rails_z(record):
    return sorted({round(z, 6) for _, _, z in record.world_vertices()})


def connected(record):
    """Every vertex reachable from vertex 0 through shared faces."""
    neighbours = {index: set() for index in range(len(record.vertices))}
    for face in record.faces:
        for index in face:
            neighbours[index].update(face)
    seen = {0}
    stack = [0]
    while stack:
        for index in neighbours[stack.pop()]:
            if index not in seen:
                seen.add(index)
                stack.append(index)
    return len(seen) == len(record.vertices)


class SingleWingTests(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(build_body(one_wing()).fingerprint(),
                         build_body(one_wing()).fingerprint())

    def test_course_rails_land_at_declared_heights(self):
        record = build_body(one_wing())
        for z in (0.0, 0.35, 3.55, 3.83):
            self.assertIn(z, rails_z(record))
        (x0, y0, z0), (x1, y1, z1) = record.bounds()
        # The cornice projects furthest, so it sets the street plane; the origin
        # is the wing's own setback, hence the negative reach.
        self.assertAlmostEqual(x0, -0.22)
        self.assertAlmostEqual(x1, 4.0)
        self.assertAlmostEqual(y0, -3.0)
        self.assertAlmostEqual(y1, 3.0)
        self.assertAlmostEqual(z0, 0.0)
        self.assertAlmostEqual(z1, 3.83)
        self.assertEqual(record.role, "body")
        self.assertIsNone(record.parent_role)
        self.assertEqual(record.metadata["wings"], ["main"])
        self.assertAlmostEqual(record.metadata["eaveZ"]["main"], 3.83)

    def test_widening_moves_rails_without_scaling_courses(self):
        narrow = build_body(one_wing())
        wide = BuildingRecipe(
            id="test_house", version=1,
            wings=(Wing("main", 0.0, 9.0, 4.0, courses=courses()),), roof=())
        wide_record = build_body(wide)
        self.assertEqual(rails_z(narrow), rails_z(wide_record))
        self.assertAlmostEqual(wide_record.bounds()[1][1], 4.5)


class FuseTests(unittest.TestCase):
    def recipe(self):
        return BuildingRecipe(
            id="ell", version=1,
            wings=(Wing("front", -1.0, 8.0, 4.0, courses=courses()),
                   Wing("back", 3.0, 6.0, 7.0, setback=2.0, courses=courses())),
            roof=())

    def test_overlapping_wings_make_one_connected_solid(self):
        record = build_body(self.recipe())  # validate() already rejects twin faces
        self.assertTrue(connected(record))
        self.assertEqual(record.metadata["wings"], ["front", "back"])


class OpeningTests(unittest.TestCase):
    def recipe(self, **overrides):
        fields = dict(id="door", kind="door", wing="main", lane_offset=0.0,
                      width=1.1, height=2.1)
        fields.update(overrides)
        return BuildingRecipe(
            id="with_door", version=1,
            wings=(Wing("main", 0.0, 6.0, 4.0, courses=courses()),),
            roof=(), openings=(Opening(**fields),))

    def test_aperture_is_a_real_hole(self):
        plain = build_body(one_wing())
        cut = build_body(self.recipe())
        self.assertGreater(len(cut.faces), len(plain.faces))
        self.assertEqual(cut.metadata["openings"], ["door:door"])
        # Nothing on any street-facing plane may cover the middle of the doorway.
        for face in cut.faces:
            points = [cut.vertices[index] for index in face]
            if max(x for x, _, _ in points) > 0.001:
                continue
            if abs(min(x for x, _, _ in points) - max(x for x, _, _ in points)) > 1e-6:
                continue
            covers = (min(y for _, y, _ in points) < 0.0 < max(y for _, y, _ in points)
                      and min(z for _, _, z in points) < 1.05 < max(z for _, _, z in points))
            self.assertFalse(covers, "a face spans the aperture")

    def test_aperture_crossing_the_wing_edge_is_an_error(self):
        with self.assertRaisesRegex(GrammarError, "door"):
            build_body(self.recipe(lane_offset=2.8))

    def test_aperture_crossing_an_inset_change_is_an_error(self):
        with self.assertRaisesRegex(GrammarError, "cannot fit inside"):
            build_body(self.recipe(height=3.7))


class GableTests(unittest.TestCase):
    def wing(self):
        return Wing("main", 0.0, 6.0, 4.0,
                    courses=courses() + (Course("gable_cap", 2.0, "whitewash"),))

    def test_cap_without_a_roof_section_is_an_error(self):
        recipe = BuildingRecipe(id="capped", version=1, wings=(self.wing(),), roof=())
        with self.assertRaisesRegex(GrammarError, "gable_cap"):
            build_body(recipe)

    def test_cap_follows_the_roof_section(self):
        recipe = BuildingRecipe(
            id="capped", version=1, wings=(self.wing(),),
            roof=(RoofSection("main", ridge_axis="X", rise=1.6),))
        record = build_body(recipe)
        self.assertAlmostEqual(record.bounds()[1][2], 3.83 + 1.6)


class MirrorTests(unittest.TestCase):
    def test_only_the_fundamental_domain_is_emitted(self):
        recipe = BuildingRecipe(
            id="sym", version=1,
            wings=(Wing("main", 0.0, 6.0, 4.0, courses=courses()),),
            roof=(), mirror_axes=("Y",))
        record = build_body(recipe)
        self.assertTrue(all(y >= -1e-9 for _, y, _ in record.vertices))
        self.assertEqual([m.kind for m in record.modifiers], ["MIRROR"])
        self.assertEqual(record.modifiers[0].axes, ("Y",))


if __name__ == "__main__":
    unittest.main()
