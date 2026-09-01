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

    def test_modelled_scale_preserves_the_praca_world_span(self):
        contract_scale = 48.0 / 1.75
        # 23.699 lane units at the camera contract, plus the two 40 px margins.
        modelled_width = 730
        with mock.patch.object(build_town, "plate_size", return_value=(modelled_width, 240)):
            lane = build_town.lane_of("modelled.png", contract_scale)
        self.assertAlmostEqual(23.699, lane["maxY"], places=2)
        self.assertAlmostEqual(
            23.699, build_town.lane_y_for("modelled.png", 690, contract_scale), places=2)

    def test_invalid_screen_scale_fails_loudly(self):
        for value in (None, 0, -1, True, "34.6"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_town.screen_scale({"id": "bad", "pixels_per_y": value})


if __name__ == "__main__":
    unittest.main()
