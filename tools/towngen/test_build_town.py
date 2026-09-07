"""Focused tests for St. Maria's per-screen plate scale."""

import pathlib
import sys
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_town  # noqa: E402


class ScreenScaleTests(unittest.TestCase):
    def test_every_generated_screen_declares_its_scale(self):
        for key, screen in build_town.SCREENS.items():
            with self.subTest(screen=key):
                self.assertGreater(build_town.screen_scale(screen), 0)

    def test_every_screen_records_plate_view_transform(self):
        for key, screen in build_town.SCREENS.items():
            with self.subTest(screen=key):
                self.assertIn(screen.get("plate_view_transform"), {"AgX", "Standard"})

    def test_plate_screens_use_current_contract_and_expected_widths(self):
        for key, screen in build_town.SCREENS.items():
            with self.subTest(screen=key):
                self.assertEqual(128, screen["plate_margin_px"])
                self.assertEqual(build_town.PIXELS_PER_Y, screen["pixels_per_y"])
                self.assertEqual(
                    build_town.EXPECTED_PLATE_WIDTHS.get(screen["plate"], screen["plate_width"]),
                    screen["plate_width"])

    def test_migration_preserves_runtime_anchor(self):
        screen = build_town.SCREENS["market"]
        self.assertAlmostEqual(22.0, build_town.stable_lane_y(screen, 801.2), places=3)
        self.assertAlmostEqual(
            128 + 22.0 * build_town.PIXELS_PER_Y,
            build_town.plate_pixel_x(screen, 801.2), places=2)

    def test_modelled_scale_preserves_the_praca_world_span(self):
        contract_scale = 48.0 / 1.75
        # The modelled Praca is 23.699 lane units plus the two 128 px margins.
        modelled_width = 906
        with mock.patch.object(build_town, "plate_size", return_value=(modelled_width, 240)):
            lane = build_town.lane_of("modelled.png", contract_scale, 128)
        self.assertAlmostEqual(23.699, lane["maxY"], places=2)
        self.assertAlmostEqual(
            23.699, build_town.lane_y_for("modelled.png", 128 + 23.699 * contract_scale,
                                          contract_scale, 128), places=2)

    def test_invalid_screen_scale_fails_loudly(self):
        for value in (None, 0, -1, True, "34.6"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_town.screen_scale({"id": "bad", "pixels_per_y": value})

    def test_promote_repaint_v4_agrees_with_expected_widths(self):
        import promote_repaint_v4
        for key, plate, width in promote_repaint_v4.SCREENS:
            with self.subTest(screen=key, plate=plate):
                self.assertEqual(
                    build_town.EXPECTED_PLATE_WIDTHS[plate],
                    width,
                    "promote_repaint_v4 width for %s must match build_town.EXPECTED_PLATE_WIDTHS" % plate,
                )


if __name__ == "__main__":
    unittest.main()

