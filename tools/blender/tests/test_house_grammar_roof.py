import math
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar.recipe import BuildingRecipe, Course, RoofSection, Wing
from house_grammar.records import face_normal
from house_grammar.roof import _Section, build_roof

EAVE = 3.0


def wing(wing_id, *, lane_offset=0.0, width=6.0, depth=5.0, setback=0.0, eave=EAVE):
    return Wing(id=wing_id, lane_offset=lane_offset, width=width, depth=depth,
                setback=setback,
                courses=(Course(kind="storey", height=eave, semantic="whitewash"),))


def recipe(wings, sections, **kwargs):
    return BuildingRecipe(id="test", version=1, wings=tuple(wings),
                          roof=tuple(sections), **kwargs)


def edge_map(record):
    """``{unordered edge: [face index, ...]}`` over the fused record."""
    edges = defaultdict(list)
    for position, face in enumerate(record.faces):
        for index in range(len(face)):
            a, b = face[index], face[(index + 1) % len(face)]
            edges[frozenset((a, b))].append(position)
    return edges


class GableCrossSectionTests(unittest.TestCase):
    """The baseline: what `Exterior.gable_roof()` draws, generalised."""

    def build(self, **kwargs):
        return build_roof(recipe([wing("main", setback=1.0)],
                                 [RoofSection(wing="main", **kwargs)]))

    def test_extents_match_the_authored_prism(self):
        record = self.build(rise=2.0, overhang=0.3, thickness=0.18)
        xs, ys, zs = zip(*record.world_vertices())
        # Footprint x in [1, 6], y in [-3, 3], expanded by the overhang on every
        # side exactly as gable_roof() does.
        self.assertAlmostEqual(min(xs), 0.7, places=6)
        self.assertAlmostEqual(max(xs), 6.3, places=6)
        self.assertAlmostEqual(min(ys), -3.3, places=6)
        self.assertAlmostEqual(max(ys), 3.3, places=6)
        self.assertAlmostEqual(max(zs), EAVE + 2.0, places=6)
        # The slab hangs below the eave, so the lowest point is the soffit.
        self.assertAlmostEqual(min(zs), EAVE - 0.18, places=6)

    def test_origin_is_the_minimum_setback(self):
        record = build_roof(recipe(
            [wing("a", setback=1.0, lane_offset=-3.5),
             wing("b", setback=2.5, lane_offset=3.5)],
            [RoofSection(wing="a"), RoofSection(wing="b")]))
        self.assertEqual(record.origin, (1.0, 0.0, 0.0))
        self.assertEqual(record.role, "roof")
        self.assertEqual(record.parent_role, "body")

    def test_ridge_offset_moves_the_peak_without_moving_the_eaves(self):
        plain = self.build(rise=2.0, overhang=0.3)
        shifted = self.build(rise=2.0, overhang=0.3, ridge_offset=0.9)
        for record, expected in ((plain, 3.5), (shifted, 4.4)):
            xs = {round(x, 6) for x, _, z in record.world_vertices()
                  if abs(z - (EAVE + 2.0)) < 1e-6}
            self.assertEqual(xs, {expected})
        # Both eaves stay where the masonry put them: the peak slid across the
        # span, it did not scale the prism.
        for record in (plain, shifted):
            xs = [x for x, _, _ in record.world_vertices()]
            self.assertAlmostEqual(min(xs), 0.7, places=6)
            self.assertAlmostEqual(max(xs), 6.3, places=6)


class ProfileTests(unittest.TestCase):
    def test_every_profile_builds_and_validates(self):
        for profile in ("gable", "hip", "half_hip", "lean_to", "cross_gable"):
            for axis in ("X", "Y"):
                with self.subTest(profile=profile, axis=axis):
                    record = build_roof(recipe(
                        [wing("main")],
                        [RoofSection(wing="main", profile=profile, ridge_axis=axis)]))
                    self.assertTrue(record.faces)
                    self.assertEqual(record.metadata["sections"]["main"]["profile"],
                                     profile)

    def test_hip_shortens_the_ridge_at_both_ends(self):
        gable = build_roof(recipe([wing("main")], [RoofSection(wing="main")]))
        hip = build_roof(recipe([wing("main")],
                                [RoofSection(wing="main", profile="hip")]))
        self.assertLess(hip.metadata["ridgeLength"], gable.metadata["ridgeLength"])
        # All four sides slope, so no vertical face reaches the ridge.
        ridge_z = EAVE + 2.0
        for x, y, z in hip.world_vertices():
            if abs(z - ridge_z) < 1e-6:
                self.assertLess(abs(y), 3.3 - 1e-6)

    def test_half_hip_keeps_more_ridge_than_a_full_hip(self):
        def ridge(profile, fraction=0.5):
            return build_roof(recipe(
                [wing("main")],
                [RoofSection(wing="main", profile=profile,
                             hip_fraction=fraction)])).metadata["ridgeLength"]
        self.assertGreater(ridge("half_hip", 0.5), ridge("hip"))
        self.assertGreater(ridge("half_hip", 0.75), ridge("half_hip", 0.25))

    def test_lean_to_has_one_slope(self):
        record = build_roof(recipe(
            [wing("main")],
            [RoofSection(wing="main", profile="lean_to", rise=1.5)]))
        peaks = {round(x, 6) for x, _, z in record.world_vertices()
                 if abs(z - (EAVE + 1.5)) < 1e-6}
        self.assertEqual(peaks, {5.3})


class SolidTests(unittest.TestCase):
    def test_thickness_makes_a_closed_solid_with_soffits(self):
        record = build_roof(recipe([wing("main")],
                                   [RoofSection(wing="main", thickness=0.22)]))
        for edge, faces in edge_map(record).items():
            self.assertEqual(len(faces), 2, f"edge {sorted(edge)} used {len(faces)}x")
        # A soffit is a downward-facing face that is not the top surface.
        downward = [face for face in record.faces
                    if face_normal(record.vertices, face)[2] < -0.5]
        self.assertTrue(downward)

    def test_a_section_is_deterministic(self):
        def once():
            return build_roof(recipe(
                [wing("a", lane_offset=-3.0), wing("b", lane_offset=3.0, setback=1.0)],
                [RoofSection(wing="a", profile="hip"),
                 RoofSection(wing="b", ridge_offset=0.4)])).fingerprint()
        self.assertEqual(once(), once())


class JunctionTests(unittest.TestCase):
    # A street-parallel range with a taller cross wing running into depth:
    # the classic valley.
    RECIPE = recipe(
        [wing("range", width=10.0, depth=5.0, eave=3.0),
         wing("cross", width=4.0, depth=8.0, eave=3.0)],
        [RoofSection(wing="range", ridge_axis="Y", rise=2.0),
         RoofSection(wing="cross", profile="cross_gable", ridge_axis="X",
                     rise=2.0)])

    def cross(self):
        return build_roof(self.RECIPE)

    def test_cross_gable_is_one_record_with_a_real_crease(self):
        record = self.cross()
        self.assertEqual(record.role, "roof")
        self.assertEqual(set(record.metadata["sections"]), {"range", "cross"})
        creased = 0
        for edge, faces in edge_map(record).items():
            self.assertEqual(len(faces), 2)
            a, b = (face_normal(record.vertices, record.faces[index]) for index in faces)
            if math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b))) > 1e-3:
                creased += 1
        self.assertGreater(creased, 0)

    def test_the_valley_dips_instead_of_being_bridged_over(self):
        """A triangle laid across the valley the wrong way tents over the dip.

        The envelope is the truth and the mesh only samples it, so a chord a
        centimetre or two proud of the dip is inevitable where the valley line
        misses a cell corner.  What must not happen is a cell tenting by a
        fraction of the rise, which is the signature of a cell picking the
        ridge diagonal inside a valley.
        """
        # 5 cm is the collar the builder confines a step to, and 1.4 px at the
        # exterior camera.  A mis-chosen diagonal here is worth ~0.4 m.
        worst = worst_tent(self.RECIPE)
        self.assertLess(worst, 0.05, f"a face tents {worst:.3f} m over the envelope")

    def test_a_higher_section_passing_over_a_lower_one_steps_rather_than_ramps(self):
        """A raised cross wing overhangs the range roof; that is a step.

        A welded height field cannot hold a vertical face, so the step has to
        become a ramp somewhere.  The collar rails are what keep that ramp
        inside 5 cm of the higher section's edge instead of letting it lean
        across the whole cell and drag the lower roof up with it.
        """
        stepped = build_roof(recipe(
            [wing("range", width=10.0, depth=5.0, eave=3.0),
             wing("cross", width=4.0, depth=8.0, eave=3.9)],
            [RoofSection(wing="range", ridge_axis="Y", rise=2.0),
             RoofSection(wing="cross", profile="cross_gable", ridge_axis="X",
                         rise=2.0)]))
        # 0.3 m clear of the cross wing's eave the range roof must still be its
        # own slope: 3.0 at its eave, rising 2.0 over the 2.8 m half span.
        for x, expected in ((0.6, 3.0 + 2.0 * 0.9 / 2.8),
                            (1.8, 3.0 + 2.0 * 2.1 / 2.8)):
            self.assertAlmostEqual(top_at(stepped, x, -2.6), expected, places=6)

    def test_no_face_is_buried_inside_the_fused_hull(self):
        record = self.cross()
        (x0, y0, z0), (x1, y1, z1) = record.bounds()
        for position, face in enumerate(record.faces):
            points = [record.vertices[index] for index in face]
            centre = [sum(axis) / len(points) for axis in zip(*points)]
            normal = face_normal(record.vertices, face)
            if abs(normal[2]) > 1e-6:
                continue  # a top or soffit face, by construction on the skin
            # Every remaining face is vertical, so it must sit on the silhouette
            # of the domain -- a fascia, never a wall left behind by a fuse.
            on_edge = any(abs(centre[axis] - bound) < 1e-6
                          for axis, bounds in ((0, (x0, x1)), (1, (y0, y1)))
                          for bound in bounds)
            interior = self.is_interior(record, centre, normal)
            self.assertFalse(interior and not on_edge,
                             f"face {position} is buried at {centre}")

    @staticmethod
    def is_interior(record, centre, normal):
        """True when solid material sits on BOTH sides of this vertical face."""
        step = 1e-3
        hits = 0
        for sign in (-1.0, 1.0):
            probe = (centre[0] + sign * step * normal[0],
                     centre[1] + sign * step * normal[1])
            for face in record.faces:
                if face_normal(record.vertices, face)[2] < 0.5:
                    continue
                points = [record.vertices[index] for index in face]
                if _in_triangle(probe, points):
                    hits += 1
                    break
        return hits == 2

    def test_same_height_neighbours_merge_into_one_run(self):
        record = build_roof(recipe(
            [wing("a", lane_offset=-3.0, width=6.0),
             wing("b", lane_offset=3.0, width=6.0)],
            [RoofSection(wing="a"), RoofSection(wing="b")]))
        # The wings abut at y = 0.  A seam would show as a vertical face whose
        # every vertex sits on that line.
        for face in record.faces:
            ys = [record.vertices[index][1] for index in face]
            self.assertFalse(all(abs(y) < 1e-6 for y in ys), "a seam wall survived")
        ys = [y for _, y, _ in record.world_vertices()]
        self.assertAlmostEqual(min(ys), -6.3, places=6)
        self.assertAlmostEqual(max(ys), 6.3, places=6)

    def test_stepped_eaves_fuse(self):
        record = build_roof(recipe(
            [wing("low", lane_offset=-3.0, eave=3.0),
             wing("high", lane_offset=3.0, eave=4.2)],
            [RoofSection(wing="low"), RoofSection(wing="high")]))
        self.assertAlmostEqual(record.metadata["sections"]["low"]["eaveZ"], 3.0)
        self.assertAlmostEqual(record.metadata["sections"]["high"]["ridgeZ"], 6.2)
        for faces in edge_map(record).values():
            self.assertEqual(len(faces), 2)


class EaveStepTests(unittest.TestCase):
    def test_eave_step_drops_only_the_plus_y_end(self):
        record = build_roof(recipe(
            [wing("main", width=6.0, depth=5.0)],
            [RoofSection(wing="main", rise=2.0, overhang=0.3, eave_step=0.5)]))
        columns = defaultdict(list)
        for x, y, z in record.world_vertices():
            columns[(round(x, 6), round(y, 6))].append(z)
        self.assertAlmostEqual(max(columns[(-0.3, -3.3)]), 3.0, places=6)
        self.assertAlmostEqual(max(columns[(-0.3, 3.3)]), 2.5, places=6)
        # The ridge stays straight across the whole length.
        self.assertAlmostEqual(max(columns[(2.5, -3.3)]), 5.0, places=6)
        self.assertAlmostEqual(max(columns[(2.5, 3.3)]), 5.0, places=6)


class MirrorTests(unittest.TestCase):
    def test_mirrored_recipe_emits_only_the_fundamental_domain(self):
        record = build_roof(recipe(
            [wing("main", width=6.0)], [RoofSection(wing="main")],
            mirror_axes=("Y",)))
        for _, y, _ in record.world_vertices():
            self.assertGreaterEqual(y, -1e-9)
        self.assertEqual([modifier.kind for modifier in record.modifiers], ["MIRROR"])
        self.assertEqual(record.modifiers[0].axes, ("Y",))

    def test_baked_axis_emits_the_whole_roof(self):
        record = build_roof(recipe(
            [wing("main", width=6.0)], [RoofSection(wing="main")],
            baked_axes=("Y",)))
        self.assertEqual(record.modifiers, ())
        self.assertLess(min(y for _, y, _ in record.world_vertices()), -3.0)


def top_at(record, x, y):
    """Height of the record's top surface at a plan point, by interpolation."""
    ox, oy, _ = record.origin
    for face in record.faces:
        if face_normal(record.vertices, face)[2] < 0.5:
            continue
        points = [(vx + ox, vy + oy, vz)
                  for vx, vy, vz in (record.vertices[index] for index in face)]
        if not _in_triangle((x, y), points):
            continue
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = points[:3]
        area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        wa = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / area
        wb = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / area
        return wa * az + wb * bz + (1.0 - wa - wb) * cz
    raise AssertionError(f"no top face covers ({x}, {y})")


def worst_tent(building):
    """The most any upward face rides above the true envelope, in metres."""
    record = build_roof(building)
    sections = [_Section(spec, building.wing(spec.wing), order)
                for order, spec in enumerate(building.roof)]
    ox, oy, _ = record.origin
    worst = 0.0
    for face in record.faces:
        if face_normal(record.vertices, face)[2] < 0.5:
            continue
        points = [record.vertices[index] for index in face]
        cx, cy, cz = (sum(axis) / len(points) for axis in zip(*points))
        cx, cy = cx + ox, cy + oy
        envelope = max(section.z(cx, cy) for section in sections
                       if section.contains(cx, cy))
        worst = max(worst, cz - envelope)
    return worst


def _in_triangle(point, points):
    """Point-in-polygon in plan, for the buried-face probe."""
    x, y = point
    inside = False
    count = len(points)
    for index in range(count):
        ax, ay = points[index][0], points[index][1]
        bx, by = points[(index + 1) % count][0], points[(index + 1) % count][1]
        if (ay > y) != (by > y):
            crossing = ax + (y - ay) / (by - ay) * (bx - ax)
            if x < crossing:
                inside = not inside
    return inside


if __name__ == "__main__":
    unittest.main()
