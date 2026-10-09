"""Blender integration proof for canonical environment-package walk semantics."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLENDER_TOOLS = ROOT / "tools" / "blender"
sys.path.insert(0, str(BLENDER_TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_test_support
import build_synthetic_environment
import town_environment_pipeline


def add_walk_semantics(blend_path: Path) -> None:
    """Augment the ordinary synthetic environment with authored semantic faces."""

    blender = blender_test_support.blender_executable()
    script = tempfile.NamedTemporaryFile(
        prefix="add_walk_semantics_", suffix=".py", delete=False,
        mode="w", encoding="utf-8"
    )
    script.write(
        "import bpy\n"
        "from pathlib import Path\n"
        f"blend_path = Path({str(blend_path)!r})\n"
        "root = bpy.context.scene.collection\n"
        "def collection(name):\n"
        "    existing = bpy.data.collections.get(name)\n"
        "    if existing is not None:\n"
        "        bpy.data.collections.remove(existing)\n"
        "    value = bpy.data.collections.new(name)\n"
        "    root.children.link(value)\n"
        "    return value\n"
        "def face_object(collection_value, name, vertices, location):\n"
        "    mesh = bpy.data.meshes.new(name + '_mesh')\n"
        "    mesh.from_pydata(vertices, [], [tuple(range(len(vertices)))])\n"
        "    mesh.update()\n"
        "    obj = bpy.data.objects.new(name, mesh)\n"
        "    obj.location = location\n"
        "    collection_value.objects.link(obj)\n"
        "    return obj\n"
        "walkable = collection('TH_WALKABLE')\n"
        "obstacles = collection('TH_OBSTACLES')\n"
        "face_object(walkable, 'SEM_Walkable_Main', "
        "[(-2,-1,0),(2,-1,0),(2,1,0),(-2,1,0)], (0.5,0.25,0))\n"
        "face_object(obstacles, 'SEM_Obstacle_Crate', "
        "[(-0.25,-0.25,0),(0.25,-0.25,0),(0.25,0.25,0),(-0.25,0.25,0)], "
        "(0.75,0.25,0))\n"
        "bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))\n"
    )
    script.close()
    try:
        result = subprocess.run([
            blender, "--background", "--factory-startup", str(blend_path),
            "--python-exit-code", "1", "--python", script.name,
        ], capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(
                "could not add walk semantics to synthetic fixture\n"
                + result.stdout + "\n" + result.stderr
            )
    finally:
        Path(script.name).unlink(missing_ok=True)


class EnvironmentPipelineWalkSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blender_test_support.blender_executable()
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_env_walk_surface_"))
        cls.fixture = cls.temp_dir / "semantic_environment.blend"
        cls.output = cls.temp_dir / "package"
        build_synthetic_environment.generate_synthetic_blend(cls.fixture)
        add_walk_semantics(cls.fixture)
        cls.export_result = town_environment_pipeline.export_environment_package(
            cls.fixture, cls.output, atlas_size=128, bake_samples=1
        )
        cls.manifest = json.loads((cls.output / "environment.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_one_canonical_export_emits_walk_surface(self):
        surface = self.manifest.get("walkSurface")
        self.assertIsInstance(surface, dict)
        self.assertEqual(surface["groundZ"], 0.0)
        self.assertEqual(len(surface["regions"]), 1)
        self.assertEqual(len(surface["obstacles"]), 1)
        self.assertEqual(surface["regions"][0]["points"], [
            [-1.5, -0.75], [2.5, -0.75], [2.5, 1.25], [-1.5, 1.25]
        ])
        self.assertEqual(surface["obstacles"][0]["points"], [
            [0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]
        ])

    def test_manifest_records_blender_semantic_authority(self):
        self.assertEqual(
            self.manifest["provenance"]["walkSurfaceAuthority"],
            "Blender collections TH_WALKABLE/TH_OBSTACLES",
        )
        self.assertIn("Compiled walk surface: 1 regions, 1 obstacles, groundZ=0",
                      self.export_result.stdout)

    def test_semantic_geometry_never_leaks_into_render_or_collision_mesh(self):
        render_text = (self.output / "environment.obj").read_text(encoding="utf-8")
        collision_text = (self.output / "collision.obj").read_text(encoding="utf-8")
        for marker in ("SEM_Walkable_Main", "SEM_Obstacle_Crate"):
            self.assertNotIn(marker, render_text)
            self.assertNotIn(marker, collision_text)


if __name__ == "__main__":
    unittest.main()
