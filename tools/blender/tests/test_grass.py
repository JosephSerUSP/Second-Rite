import math
import sys
import unittest

sys.path.insert(0, "tools/blender")
import grass
import tree_mesh


def _bases(verts, faces):
    """Lowest corner of each card, i.e. where the tuft meets the ground."""
    return [min(verts[index][2] for index in face) for face in faces]


class GrassScatterTests(unittest.TestCase):
    def test_scatter_is_deterministic(self):
        spec = grass.GrassSpec(seed=7)
        self.assertEqual(grass.scatter(spec, 4.0, 3.0), grass.scatter(spec, 4.0, 3.0))

    def test_seed_changes_the_arrangement(self):
        a = grass.scatter(grass.GrassSpec(seed=1), 4.0, 3.0)[0]
        b = grass.scatter(grass.GrassSpec(seed=2), 4.0, 3.0)[0]
        self.assertNotEqual(a, b)

    def test_density_buys_tufts_not_taller_blades(self):
        # The lesson the foliage cards already taught: a denser population must
        # not grow bigger individuals.
        spans, counts = set(), []
        for density in (4.0, 10.0, 20.0):
            verts, faces, _uvs = grass.scatter(
                grass.GrassSpec(density=density), 4.0, 4.0)
            counts.append(len(faces))
            spans.add(round(max(max(math.dist(verts[a], verts[b])
                                    for a in face for b in face)
                                for face in faces), 6))
        self.assertEqual(len(spans), 1, f"blade size tracked density: {spans}")
        self.assertLess(counts[0], counts[-1])

    def test_patch_area_scales_the_population(self):
        spec = grass.GrassSpec(density=6.0)
        small = len(grass.scatter(spec, 2.0, 2.0)[1])
        large = len(grass.scatter(spec, 4.0, 4.0)[1])
        self.assertGreater(large, small)

    def test_tufts_are_rooted_inside_the_patch(self):
        # Cards at the edge legitimately overhang -- real grass does -- so the
        # patch bounds where a tuft is ROOTED, not where its corners reach.
        verts, faces, _uvs = grass.scatter(grass.GrassSpec(), 5.0, 3.0,
                                           origin=(10.0, -2.0, 0.0))
        for face in faces:
            corners = [verts[index] for index in face]
            root = (sum(c[0] for c in corners) / 4, sum(c[1] for c in corners) / 4)
            self.assertGreaterEqual(root[0], 10.0 - 2.5 - 1e-6)
            self.assertLessEqual(root[0], 10.0 + 2.5 + 1e-6)
            self.assertGreaterEqual(root[1], -2.0 - 1.5 - 1e-6)
            self.assertLessEqual(root[1], -2.0 + 1.5 + 1e-6)

    def test_blades_rise_from_the_surface_rather_than_straddling_it(self):
        verts, faces, _uvs = grass.scatter(grass.GrassSpec(lean_deg=0.0), 3.0, 3.0)
        for base in _bases(verts, faces):
            self.assertAlmostEqual(base, 0.0, places=6)

    def test_scatter_follows_a_height_field(self):
        def ramp(x, _y):
            return x * .25, (0.0, 0.0, 1.0)
        verts, faces, _uvs = grass.scatter(grass.GrassSpec(lean_deg=0.0), 4.0, 2.0,
                                           surface=ramp)
        for face in faces:
            corners = [verts[index] for index in face]
            x = sum(c[0] for c in corners) / 4
            self.assertAlmostEqual(min(c[2] for c in corners), x * .25, places=6)

    def test_slope_limit_thins_the_scatter(self):
        def bank(_x, _y):
            tilt = math.radians(55.0)
            return 0.0, (math.sin(tilt), 0.0, math.cos(tilt))
        flat = len(grass.scatter(grass.GrassSpec(), 4.0, 4.0)[1])
        steep = len(grass.scatter(grass.GrassSpec(), 4.0, 4.0, surface=bank)[1])
        self.assertEqual(steep, 0)
        self.assertGreater(flat, 0)
        permissive = len(grass.scatter(grass.GrassSpec(slope_limit_deg=70.0),
                                       4.0, 4.0, surface=bank)[1])
        self.assertGreater(permissive, 0)

    def test_population_respects_the_vertex_ceiling(self):
        spec = grass.GrassSpec(density=5000.0)
        verts, faces, uvs = grass.scatter(spec, 10.0, 10.0)
        self.assertLessEqual(len(verts), spec.max_vertices)
        self.assertEqual(len(uvs), sum(len(face) for face in faces))

    def test_cards_are_crossed_pairs(self):
        verts, faces, _uvs = grass.scatter(grass.GrassSpec(density=3.0), 2.0, 2.0)
        self.assertEqual(len(faces) % 2, 0)
        self.assertEqual(len(verts), len(faces) * 4)

    def test_a_tuft_uses_exactly_one_atlas_cell(self):
        _v, faces, uvs = grass.scatter(
            grass.GrassSpec(atlas_columns=4, atlas_cells=(0, 1, 2, 3)), 4.0, 4.0)
        for card in range(len(faces)):
            corners = uvs[card * 4:(card + 1) * 4]
            columns = {u for u, _v in corners}
            self.assertEqual(len(columns), 2)
            lo, hi = sorted(columns)
            self.assertAlmostEqual(hi - lo, .25, places=6)

    def test_a_field_varies_its_tuft_silhouette(self):
        # One repeated silhouette is visible as a pattern at these densities.
        _v, _f, uvs = grass.scatter(grass.GrassSpec(density=12.0), 4.0, 4.0)
        self.assertGreater(len({round(u, 4) for u, _v in uvs}), 2)

    def test_a_single_cell_selection_is_honoured(self):
        _v, _f, uvs = grass.scatter(
            grass.GrassSpec(atlas_columns=4, atlas_cells=(2,)), 2.0, 2.0)
        self.assertEqual({round(u, 4) for u, _v in uvs}, {.5, .75})

    def test_grass_shares_the_foliage_card_builder(self):
        # A blade and a branch spray must stay the same kind of object.
        self.assertIs(grass.card_corners, tree_mesh.card_corners)
        self.assertIs(grass.atlas_uvs, tree_mesh.atlas_uvs)

    def test_rejects_a_degenerate_patch(self):
        for width, depth in ((0.0, 2.0), (2.0, -1.0)):
            with self.assertRaises(ValueError):
                grass.scatter(grass.GrassSpec(), width, depth)


if __name__ == "__main__":
    unittest.main()
