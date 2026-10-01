"""Contract for adjustable shared door/window geometry families."""

from pathlib import Path
import sys
import unittest

RECIPES = Path(__file__).resolve().parents[1] / "recipes"
sys.path.insert(0, str(RECIPES))
from opening_families import door, window  # noqa: E402


class Part(dict):
    def __init__(self, name, size, location, material):
        super().__init__()
        self.name = name
        self.size = size
        self.location = location
        self.material = material


class Host:
    back_x = 9.0
    wood = "wood"
    stone = "stone"
    terracotta = "terracotta"
    glass = "glass"
    window_glow = "glow"
    iron = "iron"
    panel = "panel"

    def __init__(self):
        self.parts = []

    def y(self, lane_y):
        return 12.0 - lane_y

    def part(self, name, size, location, material):
        part = Part(name, size, location, material)
        self.parts.append(part)
        return part


class OpeningFamiliesTests(unittest.TestCase):
    def test_door_family_morphs_width_height_panels_and_anchor(self):
        host = Host()
        parts = door(host, "inn", 4.0, width=1.4, height=2.45, x=4.3,
                     panels=4, panel_material=host.panel)
        leaf = next(part for part in parts if part.name == "inn_leaf")
        self.assertEqual(leaf.size, (0.12, 1.4, 2.45))
        self.assertEqual(leaf.location, (4.285, 8.0, 1.225))
        self.assertEqual(sum("panel_" in part.name for part in parts), 4)
        self.assertTrue(all(part.material == host.panel for part in parts
                            if "panel_" in part.name))

    def test_plain_door_family_does_not_force_panels(self):
        parts = door(Host(), "plain", 2.0)
        self.assertFalse(any("panel_" in part.name for part in parts))

    def test_window_family_morphs_sill_and_optional_shutters(self):
        host = Host()
        parts = window(host, "guest", 7.0, width=1.2, height=1.5,
                       sill_z=1.7, shutters=False, source=True)
        pane = next(part for part in parts if part.name == "guest_pane")
        self.assertEqual(pane.size, (0.08, 1.2, 1.5))
        self.assertEqual(pane.location, (8.985, 5.0, 2.45))
        self.assertFalse(any("shutter" in part.name for part in parts))
        self.assertTrue(all(part.get("sr_bake_role") == "source"
                            for part in parts))

    def test_recess_and_retained_silhouette_do_not_export_panel_relief(self):
        parts=window(Host(), 'court', 3, x=4.35, recess=.15,
                     source=True, retain_shape=True,joinery_material='paint',shutter_material='sage')
        lookup={part.name:part for part in parts}
        self.assertAlmostEqual(lookup['court_pane'].location[0],4.485)
        self.assertEqual(lookup['court_jamb_l']['sr_bake_role'],'both')
        self.assertEqual(lookup['court_shutter_l']['sr_bake_role'],'both')
        self.assertEqual(lookup['court_shutter_l'].material,'paint')
        self.assertEqual(lookup['court_shutter_l_panel_0']['sr_bake_role'],'source')
        self.assertEqual(lookup['court_shutter_l_panel_0'].material,'sage')

    def test_grille_is_spaced_bars_and_invalid_openings_fail(self):
        parts=window(Host(),'iron',3,grille=True,shutters=False)
        bars=[part for part in parts if part.name.startswith('iron_grille_')]
        self.assertEqual(len(bars),4)
        self.assertTrue(all(part.size[1]<.03 for part in bars))
        with self.assertRaises(ValueError):window(Host(),'bad',0,recess=-.1)
        with self.assertRaises(ValueError):door(Host(),'bad',0,width=0)


if __name__ == "__main__":
    unittest.main()
