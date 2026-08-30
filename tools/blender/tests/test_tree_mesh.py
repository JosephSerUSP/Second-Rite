import math
import sys
import unittest

sys.path.insert(0, "tools/blender")
import tree_generator as trees
import tree_mesh


def _low(name="round_shade"):
    return trees.reduce_lod(trees.generate(trees.preset(name), "authoring"), "low")


class BranchMeshTests(unittest.TestCase):
    def test_every_preset_meshes_within_bridge_limits(self):
        for name in trees.PRESETS:
            verts, faces = tree_mesh.branch_mesh(_low(name))
            self.assertLessEqual(len(verts), 1024, name)
            self.assertLessEqual(len(faces), 1024, name)
            self.assertTrue(all(len(face) >= 3 for face in faces))
            self.assertTrue(all(0 <= index < len(verts) for face in faces for index in face))

    def test_faces_are_unique_so_bmesh_can_create_them_all(self):
        # add_geometry fails the whole request on a duplicate face, so the
        # mesher must never emit the same corner set twice.
        _verts, faces = tree_mesh.branch_mesh(_low("weeping"))
        self.assertEqual(len(faces), len({frozenset(face) for face in faces}))

    def test_forks_share_one_parent_ring(self):
        # The point of the node-ring builder: N segments produce N+1 rings,
        # never one ring pair per segment.
        skeleton = _low("conical")
        for sides in (6, 8):
            verts, _faces = tree_mesh.branch_mesh(skeleton, sides=sides)
            self.assertEqual(len(verts), (len(skeleton.segments) + 1) * sides)

    def test_mesh_is_deterministic_and_honours_origin(self):
        skeleton = _low("umbrella")
        first, faces = tree_mesh.branch_mesh(skeleton)
        second, _ = tree_mesh.branch_mesh(skeleton)
        self.assertEqual(first, second)
        moved, moved_faces = tree_mesh.branch_mesh(skeleton, origin=(1.0, 2.0, 3.0))
        self.assertEqual(faces, moved_faces)
        for before, after in zip(first, moved):
            self.assertAlmostEqual(after[0] - before[0], 1.0, places=6)
            self.assertAlmostEqual(after[2] - before[2], 3.0, places=6)

    def test_ring_radius_follows_the_skeleton_taper(self):
        skeleton = _low("columnar")
        verts, _faces = tree_mesh.branch_mesh(skeleton, sides=6)
        def ring_radius(node):
            ring = verts[node * 6:(node + 1) * 6]
            centre = [sum(axis) / 6 for axis in zip(*ring)]
            return sum(math.dist(point, centre) for point in ring) / 6
        # Node 0 is the root; the last node is a terminal twig.
        self.assertGreater(ring_radius(0), ring_radius(len(skeleton.segments)))

    def test_rejects_degenerate_input(self):
        with self.assertRaises(ValueError):
            tree_mesh.branch_mesh(_low(), sides=2)


class FoliageMeshTests(unittest.TestCase):
    def test_cards_carry_one_uv_per_face_corner(self):
        skeleton = _low("round_shade")
        verts, faces, uvs = tree_mesh.foliage_mesh(skeleton, lod="low")
        self.assertEqual(len(faces), len(skeleton.foliage_carriers) * 2)
        self.assertEqual(len(verts), len(faces) * 4)
        self.assertEqual(len(uvs), sum(len(face) for face in faces))
        self.assertTrue(all(0.0 <= u <= 1.0 and 0.0 <= v <= 1.0 for u, v in uvs))

    def test_uvs_stay_inside_the_chosen_atlas_cell(self):
        _v, _f, uvs = tree_mesh.foliage_mesh(_low(), atlas_columns=4, atlas_cell=2)
        self.assertEqual({u for u, _v in uvs}, {0.5, 0.75})

    def test_every_lod_crosses_each_card(self):
        # A lone plane vanishes edge-on; both LODs must emit the pair.
        for lod in ("authoring", "low"):
            skeleton = trees.generate(trees.preset("umbrella"), "authoring")
            if lod == "low":
                skeleton = trees.reduce_lod(skeleton, lod)
            _v, faces, _uvs = tree_mesh.foliage_mesh(skeleton, lod=lod)
            self.assertEqual(len(faces), len(skeleton.foliage_carriers) * 2, lod)

    def test_cards_stay_within_bridge_limits(self):
        for name in trees.PRESETS:
            skeleton = trees.reduce_lod(trees.generate(trees.preset(
                name, height=6.6, crown_radius=2.1), "authoring"), "low")
            verts, faces, _uvs = tree_mesh.foliage_mesh(skeleton, lod="low")
            self.assertLessEqual(len(verts), 1024, name)
            self.assertLessEqual(len(faces), 1024, name)

    def test_cards_reach_past_their_supporting_branch(self):
        # A card centred on a short twig is what produced the pinched, bald
        # silhouette; the span must exceed the carrier segment it sits on.
        skeleton = _low("young")
        verts, faces, _uvs = tree_mesh.foliage_mesh(skeleton)
        by_index = {s.index: s for s in skeleton.segments}
        for face, carrier in zip(faces, skeleton.foliage_carriers):
            corners = [verts[index] for index in face]
            span = max(math.dist(a, b) for a in corners for b in corners)
            segment = by_index[carrier.segment_index]
            self.assertGreater(span, math.dist(segment.start, segment.end))

    def test_leaf_size_does_not_grow_with_crown_radius(self):
        # A wider crown must be filled with MORE sprays, never with bigger
        # ones: apparent leaf scale is a property of the foliage, and near the
        # camera an oversized silhouette reads as a houseplant, not a tree.
        spans, counts = set(), []
        for crown_radius in (1.6, 2.1, 2.6, 3.2):
            skeleton = trees.reduce_lod(trees.generate(trees.preset(
                "round_shade", height=5.0, crown_radius=crown_radius),
                "authoring"), "low")
            verts, faces, _uvs = tree_mesh.foliage_mesh(skeleton, lod="low")
            widest = max(max(math.dist(verts[a], verts[b]) for a in face for b in face)
                         for face in faces)
            spans.add(round(widest, 6))
            counts.append(len(skeleton.foliage_carriers))
        self.assertEqual(len(spans), 1, f"leaf size varied with crown radius: {spans}")
        # Coverage is bought with count instead.
        self.assertGreater(counts[-1], counts[0])

    def test_spray_extent_follows_the_authored_spray_length(self):
        skeleton = _low()
        small = trees.reduce_lod(trees.generate(trees.preset(
            "round_shade", spray_length=1.0), "authoring"), "low")
        def widest(sk):
            verts, faces, _uvs = tree_mesh.foliage_mesh(sk, lod="low")
            return max(max(math.dist(verts[a], verts[b]) for a in face for b in face)
                       for face in faces)
        self.assertLess(widest(small), widest(skeleton))


class CrownAndBoleShapeTests(unittest.TestCase):
    """Shape assertions.

    The suite could previously not tell a plaza tree from a pole with a hat:
    it checked budgets, determinism and connectivity, never proportion.
    """

    def _plaza(self, name="round_shade"):
        spec = trees.preset(name, height=6.6, crown_radius=2.1)
        return trees.reduce_lod(trees.generate(spec, "authoring"), "low")

    def test_crown_starts_near_the_authored_clear_trunk(self):
        for name in trees.PRESETS:
            # Each preset at its authored height; forcing a sapling to plaza
            # scale tests the override, not the preset.
            skeleton = trees.reduce_lod(
                trees.generate(trees.preset(name), "authoring"), "low")
            spec = skeleton.spec
            by_index = {s.index: s for s in skeleton.segments}
            lowest = min(by_index[c.segment_index].end[2]
                         for c in skeleton.foliage_carriers)
            asked = spec.clear_trunk * spec.height
            # A crown cannot begin closer to the ground than one branch
            # segment above its lowest attachment, but it may not float any
            # higher than that above the authored clear trunk.
            self.assertLessEqual(lowest, asked + spec.segment_length, name)
            if name == "weeping":
                # A weeping crown descending past its own clear trunk is the
                # entire point of the preset, not a defect.
                self.assertLess(lowest, asked)
            else:
                self.assertGreaterEqual(lowest, asked * .85, name)

    def test_the_clear_bole_actually_tapers(self):
        skeleton = self._plaza()
        trunk = [s for s in skeleton.segments if s.level == 0]
        self.assertGreater(len(trunk), 3)
        for lower, upper in zip(trunk, trunk[1:]):
            self.assertLess(upper.radius, lower.radius)
        # A cylinder loses a few percent; a bole loses most of its radius.
        self.assertLess(trunk[-1].radius, trunk[0].radius * .5)

    def test_the_bole_flares_where_it_meets_the_ground(self):
        skeleton = self._plaza()
        verts, _faces = tree_mesh.branch_mesh(skeleton, sides=6)
        def ring_radius(node):
            ring = verts[node * 6:(node + 1) * 6]
            centre = [sum(axis) / 6 for axis in zip(*ring)]
            return sum(math.dist(point, centre) for point in ring) / 6
        self.assertGreater(ring_radius(0), ring_radius(1) * 1.15)

    def test_lower_limbs_leave_the_trunk_more_horizontally(self):
        skeleton = trees.generate(trees.preset("round_shade", height=6.6,
                                               crown_radius=2.1), "authoring")
        by_index = {s.index: s for s in skeleton.segments}
        first = {}
        for segment in skeleton.segments:
            if segment.level != 1 or segment.parent not in by_index:
                continue
            if by_index[segment.parent].level != 0:
                continue
            rise = segment.end[2] - segment.start[2]
            run = math.hypot(segment.end[0] - segment.start[0],
                             segment.end[1] - segment.start[1])
            first[segment.start[2]] = rise / max(1e-6, run)
        heights = sorted(first)
        self.assertGreaterEqual(len(heights), 3)
        self.assertLess(first[heights[0]], first[heights[-1]])


if __name__ == "__main__":
    unittest.main()
