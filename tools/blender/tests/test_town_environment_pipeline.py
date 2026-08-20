"""Tests for the Blender baked environment pipeline (Second Gate town slice spike)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLENDER_TOOLS = ROOT / "tools" / "blender"
sys.path.insert(0, str(BLENDER_TOOLS))

import build_synthetic_environment
import town_environment_pipeline


class TownEnvironmentPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_env_pipeline_"))
        cls.fixture_blend = cls.temp_dir / "town_slice_fixture.blend"
        cls.output_dir = cls.temp_dir / "exported_package"
        # 1. Build synthetic fixture
        build_synthetic_environment.generate_synthetic_blend(cls.fixture_blend)
        # 2. Run pipeline
        town_environment_pipeline.export_environment_package(
            cls.fixture_blend, cls.output_dir, atlas_size=256, bake_samples=4
        )
        manifest_path = cls.output_dir / "environment.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_only_th_render_exports_as_render_mesh(self):
        obj_file = self.output_dir / "environment.obj"
        self.assertTrue(obj_file.is_file())
        content = obj_file.read_text(encoding="utf-8")

        # Object name should reflect RND_Environment_Mesh
        self.assertIn("RND_Environment_Mesh", content)
        # TH_SOURCE, TH_COLLISION, TH_PREVIEW_ACTORS, TH_PREVIEW_ONLY should never appear in render OBJ
        self.assertNotIn("SRC_", content)
        self.assertNotIn("COL_", content)
        self.assertNotIn("ACTOR_", content)
        self.assertNotIn("GUIDE_", content)

    def test_exactly_one_beauty_texture_referenced(self):
        texture_file = self.output_dir / "environment.png"
        self.assertTrue(texture_file.is_file())
        self.assertGreater(texture_file.stat().st_size, 0)

        mtl_file = self.output_dir / "environment.mtl"
        self.assertTrue(mtl_file.is_file())
        mtl_text = mtl_file.read_text(encoding="utf-8")

        # Must have exactly one newmtl and one map_Kd referencing environment.png
        newmtl_count = mtl_text.count("newmtl ")
        map_kd_count = mtl_text.count("map_Kd ")
        self.assertEqual(newmtl_count, 1)
        self.assertEqual(map_kd_count, 1)
        self.assertIn("map_Kd environment.png", mtl_text)

    def test_preview_actors_never_leak_into_bake_or_export(self):
        # 1. Check render mesh OBJ
        obj_text = (self.output_dir / "environment.obj").read_text(encoding="utf-8")
        self.assertNotIn("Walker", obj_text)
        self.assertNotIn("ACTOR", obj_text)

        # 2. Check collision OBJ
        col_text = (self.output_dir / "collision.obj").read_text(encoding="utf-8")
        self.assertNotIn("Walker", col_text)
        self.assertNotIn("ACTOR", col_text)

        # 3. Check anchors
        anchors = self.manifest.get("anchors", {})
        for name in anchors:
            self.assertFalse(name.startswith("ACTOR"), f"Actor leaked into anchors: {name}")
            self.assertNotIn("walker", name.lower())

    def test_anchors_have_stable_deterministic_transforms(self):
        anchors = self.manifest.get("anchors", {})
        expected_anchors = ["spawn_player", "npc_elder", "torch_mount", "shop_counter"]
        for name in expected_anchors:
            self.assertIn(name, anchors)
            anchor = anchors[name]
            self.assertIn("position", anchor)
            self.assertIn("rotation", anchor)
            self.assertIn("forward", anchor)
            self.assertEqual(len(anchor["position"]), 3)
            self.assertEqual(len(anchor["forward"]), 3)

        # spawn_player should be at origin-ish area facing forward
        spawn = anchors["spawn_player"]
        self.assertEqual(spawn["position"], [0.0, 0.5, 0.0])
        self.assertEqual(spawn["forward"], [0.0, 1.0, 0.0])

    def test_collision_exports_independently(self):
        col_file = self.output_dir / "collision.obj"
        self.assertTrue(col_file.is_file())
        col_text = col_file.read_text(encoding="utf-8")

        # Must contain collision objects and no render materials
        self.assertNotIn("mtllib", col_text)
        self.assertIn("v ", col_text)
        self.assertIn("f ", col_text)

    def test_coordinate_orientation_matches_thestra(self):
        # Thestra: +X East, +Y South, +Z Up
        # The manifest bounds should match the Z-up bounds
        bounds = self.manifest["bounds"]
        self.assertEqual(len(bounds), 6)
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        self.assertLess(min_x, max_x)
        self.assertLess(min_y, max_y)
        self.assertLess(min_z, max_z)
        self.assertAlmostEqual(min_z, 0.0, places=2)
        self.assertAlmostEqual(max_z, 3.0, places=2)

    def test_repeated_export_is_deterministic(self):
        output_dir_2 = self.temp_dir / "exported_package_2"
        town_environment_pipeline.export_environment_package(
            self.fixture_blend, output_dir_2, atlas_size=256, bake_samples=4
        )

        with open(output_dir_2 / "environment.json", "r", encoding="utf-8") as f:
            manifest_2 = json.load(f)

        self.assertEqual(self.manifest["stats"]["triangleCount"], manifest_2["stats"]["triangleCount"])
        self.assertEqual(self.manifest["stats"]["vertexCount"], manifest_2["stats"]["vertexCount"])
        self.assertEqual(self.manifest["bounds"], manifest_2["bounds"])
        self.assertEqual(self.manifest["anchors"], manifest_2["anchors"])

    def test_record_environment_metrics(self):
        stats = self.manifest["stats"]
        print("\n--- Town Slice Environment Spike Metrics ---")
        print(f"Triangle Count: {stats['triangleCount']}")
        print(f"Vertex Count: {stats['vertexCount']}")
        print(f"Material Groups: {stats['materialGroupCount']}")
        print(f"Atlas Dimensions: {stats['textureDimensions'][0]}x{stats['textureDimensions'][1]}")
        print(f"PNG Size: {stats['pngSizeBytes']} bytes")
        print(f"Render Mesh OBJ Size: {stats['renderMeshSizeBytes']} bytes")
        print(f"Total Package Size: {stats['packageSizeBytes']} bytes")
        print("--------------------------------------------")

        self.assertGreater(stats["triangleCount"], 0)
        self.assertGreater(stats["vertexCount"], 0)
        self.assertEqual(stats["materialGroupCount"], 1)


if __name__ == "__main__":
    unittest.main()
