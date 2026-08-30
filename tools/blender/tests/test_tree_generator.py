import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
