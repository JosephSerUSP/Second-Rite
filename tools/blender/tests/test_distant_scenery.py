import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from distant_scenery import (  # noqa: E402
    DEFAULT_MODULES,
    LANE_CENTRE_Y,
    LANE_MAX_Y,
    LANE_MIN_Y,
    STUDY_MARGIN_Y,
    coverage_bounds,
    lane_to_blender_y,
    validate_module,
    validate_modules,
)


class BackgroundBillboardContractTests(unittest.TestCase):
    def test_layout_is_source_topology_and_overscanned(self):
        self.assertTrue(validate_modules())
        self.assertGreaterEqual(len(DEFAULT_MODULES), 5)
        bounds = sorted(coverage_bounds(module) for module in DEFAULT_MODULES)
        self.assertLessEqual(bounds[0][0], -STUDY_MARGIN_Y)
        self.assertGreaterEqual(bounds[-1][1], STUDY_MARGIN_Y)
        self.assertTrue(all(module["span"] > 0 for module in DEFAULT_MODULES))

    def test_layout_has_no_unbounded_opening(self):
        bounds = sorted(coverage_bounds(module) for module in DEFAULT_MODULES)
        for left, right in zip(bounds, bounds[1:]):
            self.assertLessEqual(right[0] - left[1], 5.0)

    def test_lane_mirror_matches_adopted_source(self):
        self.assertAlmostEqual(lane_to_blender_y(LANE_CENTRE_Y), 0.0)
        self.assertAlmostEqual(lane_to_blender_y(LANE_MIN_Y), 14.875)
        self.assertAlmostEqual(lane_to_blender_y(LANE_MAX_Y), -14.875)

    def test_runtime_background_is_a_world_space_candidate(self):
        from distant_scenery import BILLBOARD_X, FLOOR_NEAR_X, PLATE_HEIGHT, PLATE_WIDTH
        self.assertEqual((PLATE_WIDTH, PLATE_HEIGHT), (866, 240))
        self.assertGreater(BILLBOARD_X, 34.0)
        self.assertLess(FLOOR_NEAR_X, -12.0)

    def test_invalid_module_fails_loudly(self):
        invalid = dict(DEFAULT_MODULES[0], span=0)
        with self.assertRaises(ValueError):
            validate_module(invalid)
        invalid = dict(DEFAULT_MODULES[0], target=(20.0, -27.0, 0.0))
        with self.assertRaises(ValueError):
            validate_module(invalid)


if __name__ == "__main__":
    unittest.main()
