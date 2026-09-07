import sys
import unittest
import math

sys.path.insert(0, "tools/blender")
import tree_generator as trees


class TreeGeneratorTests(unittest.TestCase):
    def test_seed_is_deterministic(self):
        spec = trees.preset("round_shade", seed_offset=4)
        self.assertEqual(trees.generate(spec), trees.generate(spec))

    def test_all_presets_validate_and_reduce(self):
        for name in trees.PRESETS:
            full = trees.generate(trees.preset(name), "authoring")
            low = trees.reduce_lod(full, "low")
            self.assertTrue(trees.validate(full, "authoring"))
            self.assertTrue(trees.validate(low, "low"))
            self.assertLessEqual(len(full.segments), 160)
            self.assertLessEqual(len(low.segments), 64)
            self.assertLessEqual(len(low.segments), len(full.segments))

    def test_seed_changes_topology(self):
        a = trees.generate(trees.preset("umbrella", seed_offset=1))
        b = trees.generate(trees.preset("umbrella", seed_offset=2))
        self.assertNotEqual(a.segments, b.segments)

    def test_low_foliage_carriers_have_diverse_authored_rolls(self):
        full = trees.generate(trees.preset("weeping"), "authoring")
        low = trees.reduce_lod(full, "low")
        rolls = {round(carrier.roll_radians, 5) for carrier in low.foliage_carriers}
        self.assertEqual(len(low.foliage_carriers), trees.foliage_card_budget(full))
        self.assertGreaterEqual(len(rolls), 18)
        self.assertEqual(low, trees.reduce_lod(full, "low"))

    def test_low_card_budget_tracks_foliage_support_reach(self):
        budgets = {}
        for name in trees.PRESETS:
            full = trees.generate(trees.preset(name), "authoring")
            budgets[name] = trees.foliage_card_budget(full)
        self.assertGreater(budgets["round_shade"], budgets["young"])
        self.assertGreater(budgets["weeping"], budgets["columnar"])
        self.assertGreater(len(set(budgets.values())), 3)

    def test_directed_crown_bias_moves_the_authored_envelope(self):
        base = trees.generate(trees.preset("round_shade", attraction_weight=0), "authoring")
        biased = trees.generate(trees.preset(
            "round_shade", attraction_weight=0, crown_bias=.65, crown_bias_deg=0),
            "authoring")
        base_mean = sum(point[0] for segment in base.segments
                        for point in (segment.start, segment.end)) / (2 * len(base.segments))
        biased_mean = sum(point[0] for segment in biased.segments
                          for point in (segment.start, segment.end)) / (2 * len(biased.segments))
        self.assertGreater(biased_mean, base_mean + .15)
        self.assertEqual(biased, trees.generate(trees.preset(
            "round_shade", attraction_weight=0, crown_bias=.65, crown_bias_deg=0),
            "authoring"))

    def test_apical_dominance_repositions_branch_attachments(self):
        def attachment_heights(dominance):
            skeleton = trees.generate(trees.preset(
                "columnar", attraction_weight=0, apical_dominance=dominance), "authoring")
            by_index = {segment.index: segment for segment in skeleton.segments}
            return [segment.start[2] for segment in skeleton.segments
                    if segment.level == 1 and by_index[segment.parent].level == 0]

        low = attachment_heights(0)
        high = attachment_heights(1)
        self.assertEqual(len(low), len(high))
        self.assertGreater(sum(high) / len(high), sum(low) / len(low))

    def test_branch_twist_and_attraction_are_independent_shape_controls(self):
        plain = trees.generate(trees.preset(
            "round_shade", attraction_weight=0, branch_twist_deg=0), "authoring")
        twisted = trees.generate(trees.preset(
            "round_shade", attraction_weight=0, branch_twist_deg=120), "authoring")
        steered = trees.generate(trees.preset(
            "round_shade", attraction_weight=1, influence_radius=3.0,
            kill_radius=.1, branch_twist_deg=0), "authoring")
        def primary_azimuths(skeleton):
            by_index = {segment.index: segment for segment in skeleton.segments}
            return [math.atan2(segment.end[1] - segment.start[1],
                               segment.end[0] - segment.start[0])
                    for segment in skeleton.segments
                    if segment.level == 1 and by_index[segment.parent].level == 0]
        self.assertNotEqual(primary_azimuths(plain), primary_azimuths(twisted))
        self.assertNotEqual(plain.segments, steered.segments)

    def test_new_shape_controls_are_bounded(self):
        with self.assertRaises(ValueError):
            trees.generate(trees.preset("round_shade", crown_bias=1.01))
        with self.assertRaises(ValueError):
            trees.generate(trees.preset("round_shade", branch_sweep_deg=91))
        with self.assertRaises(ValueError):
            trees.generate(trees.preset("round_shade", attraction_weight=1.01))


if __name__ == "__main__":
    unittest.main()
