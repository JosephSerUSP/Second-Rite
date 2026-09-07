"""Tests for the composable attached-structure vocabulary."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from house_grammar import build  # noqa: E402
from house_grammar.recipe import (  # noqa: E402
    BuildingRecipe, Course, GrammarError, RoofSection, VerandaSpec, Wing,
)
from house_grammar.records import validate  # noqa: E402


def recipe_with(verandas=()):
    courses = (Course("plinth", 0.35, "rough_limestone"),
               Course("storey", 3.0, "whitewash",
                      return_semantic="rough_limestone"),
               Course("cornice", 0.2, "rough_limestone"))
    return BuildingRecipe(
        id="gallery_test", version=1,
        wings=(Wing("main", 0.0, 6.0, 5.0, courses=courses),),
        roof=(RoofSection("main", rise=1.4),), attachments=verandas)


class VerandaSchemaTests(unittest.TestCase):
    def test_controls_are_quantised_and_serialised(self):
        veranda = VerandaSpec(
            "front_gallery", "main", width=4.2, depth=1.35,
            height=2.7, roof_rise=0.31, roof_thickness=0.12,
            support_count=3, support_width=0.18)
        recipe = recipe_with((veranda,))
        data = recipe.as_json()["attachments"][0]
        self.assertEqual(data["id"], "front_gallery")
        self.assertEqual(data["supportCount"], 3)
        self.assertEqual(data["roofThickness"], 0.12)

    def test_rejects_a_gallery_past_the_host_span(self):
        with self.assertRaisesRegex(GrammarError, "past wing main"):
            build(recipe_with((VerandaSpec(
                "too_wide", "main", width=6.1),)))

    def test_rejects_a_roof_that_starts_inside_the_slab(self):
        with self.assertRaisesRegex(GrammarError, "must exceed slab"):
            build(recipe_with((VerandaSpec(
                "flat", "main", height=0.16, slab=0.16,
                roof_thickness=0.02),)))


class VerandaGeometryTests(unittest.TestCase):
    def test_one_attachment_is_one_valid_parented_record(self):
        records = build(recipe_with((VerandaSpec(
            "front_gallery", "main", width=4.2, support_count=3),)))
        attachment = records[2]
        validate(attachment)
        self.assertEqual(attachment.role, "attachment:front_gallery")
        self.assertEqual(attachment.parent_role, "body")
        self.assertEqual(attachment.metadata["kind"], "veranda")
        self.assertIn("dark_wood", attachment.face_materials)
        self.assertIn("roof_tile", attachment.face_materials)
        self.assertGreater(len(attachment.faces), 12)

    def test_each_elevation_projects_away_from_its_host_wall(self):
        for elevation in ("front", "back", "left", "right"):
            with self.subTest(elevation=elevation):
                recipe = recipe_with((VerandaSpec(
                    "gallery", "main", elevation=elevation,
                    lane_offset=0.0 if elevation in ("front", "back") else 2.5,
                    width=4.0),))
                attachment = build(recipe)[2]
                world = attachment.world_vertices()
                low_x = min(point[0] for point in world)
                high_x = max(point[0] for point in world)
                low_y = min(point[1] for point in world)
                high_y = max(point[1] for point in world)
                if elevation == "front":
                    self.assertLess(low_x, 0.0)
                    self.assertLessEqual(low_y, -2.0)
                    self.assertGreaterEqual(high_y, 2.0)
                elif elevation == "back":
                    self.assertGreater(high_x, 5.0)
                elif elevation == "left":
                    self.assertLess(low_y, -3.0)
                else:
                    self.assertGreater(high_y, 3.0)

    def test_support_count_changes_geometry_not_the_record_contract(self):
        no_posts = build(recipe_with((VerandaSpec(
            "cantilever", "main", support_count=0),)))[2]
        three_posts = build(recipe_with((VerandaSpec(
            "supported", "main", support_count=3),)))[2]
        self.assertGreater(len(three_posts.faces), len(no_posts.faces))
        self.assertEqual(no_posts.role, three_posts.role.replace(
            "supported", "cantilever"))


if __name__ == "__main__":
    unittest.main()
