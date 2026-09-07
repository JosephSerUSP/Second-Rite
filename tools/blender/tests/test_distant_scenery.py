import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from distant_scenery import (  # noqa: E402
    DEFAULT_SPECS,
    LANE_CENTRE_Y,
    LANE_MAX_Y,
    LANE_MIN_Y,
    coverage_bounds,
    lane_to_blender_y,
    validate_specs,
    validate_scenery_spec,
)


class DistantSceneryContractTests(unittest.TestCase):
    def test_default_stack_has_explicit_depth_order_and_coverage(self):
        self.assertTrue(validate_specs())
        depths = [spec["depth"] for spec in DEFAULT_SPECS]
        self.assertGreaterEqual(len(set(depths)), 3)
        continuous = False
        for spec in DEFAULT_SPECS:
            minimum, maximum = coverage_bounds(spec)
            self.assertGreaterEqual(minimum, -30.0)
            self.assertLessEqual(maximum, 30.0)
            continuous = continuous or (minimum <= -30.0 and maximum >= 30.0)
        self.assertTrue(continuous)

    def test_lane_mirror_matches_adopted_source(self):
        self.assertAlmostEqual(lane_to_blender_y(LANE_CENTRE_Y), 0.0)
        self.assertAlmostEqual(lane_to_blender_y(LANE_MIN_Y), 14.875)
        self.assertAlmostEqual(lane_to_blender_y(LANE_MAX_Y), -14.875)

    def test_invalid_specs_fail_loudly(self):
        invalid = dict(DEFAULT_SPECS[0], width=0)
        with self.assertRaises(ValueError):
            validate_scenery_spec(invalid)
        invalid = dict(DEFAULT_SPECS[0], profile=((0.1, 0.2), (1.0, 0.4), (1.0, 0.2)))
        with self.assertRaises(ValueError):
            validate_scenery_spec(invalid)


if __name__ == "__main__":
    unittest.main()
