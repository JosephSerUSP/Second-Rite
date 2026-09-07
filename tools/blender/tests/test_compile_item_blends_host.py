"""Host-side unit tests for compile_item_blends.py.

Verifies project root resolution, discovery of authoritative .blend sources,
detection of missing or stale products, and rejection of silent zero-source
verification checks without requiring Blender or a display.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLENDER_TOOLS = ROOT / "tools" / "blender"

if str(BLENDER_TOOLS) not in sys.path:
    sys.path.insert(0, str(BLENDER_TOOLS))

import compile_item_blends


class TestCompileItemBlendsHost(unittest.TestCase):
    def test_default_project_discovery(self):
        project_root = compile_item_blends.DEFAULT_PROJECT_DIR
        source_dir = project_root / "assets" / "authoring" / "items"
        sources = compile_item_blends.sources_from_args([], source_dir)
        self.assertGreaterEqual(len(sources), 32)
        for src in sources:
            self.assertTrue(src.is_file())
            self.assertEqual(src.suffix, ".blend")

    def test_explicit_source_arguments(self):
        project_root = compile_item_blends.DEFAULT_PROJECT_DIR
        source_dir = project_root / "assets" / "authoring" / "items"
        existing = list(source_dir.glob("*.blend"))
        self.assertTrue(existing)
        selected = [str(existing[0])]
        sources = compile_item_blends.sources_from_args(selected, source_dir)
        self.assertEqual(sources, [existing[0].resolve()])

    def test_duplicate_source_arguments_rejected(self):
        project_root = compile_item_blends.DEFAULT_PROJECT_DIR
        source_dir = project_root / "assets" / "authoring" / "items"
        existing = list(source_dir.glob("*.blend"))
        self.assertTrue(existing)
        with self.assertRaises(SystemExit):
            compile_item_blends.sources_from_args([str(existing[0]), str(existing[0])], source_dir)

    def test_check_mode_fails_on_empty_source_discovery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_project = Path(temp_dir)
            with self.assertRaises(SystemExit) as ctx:
                compile_item_blends.main(["--blender", "dummy_blender", "--check", "--project-root", str(empty_project)])
            self.assertIn("cannot verify", str(ctx.exception))

    def test_compare_bytes_missing_expected_product(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            actual = Path(temp_dir) / "actual.obj"
            actual.write_bytes(b"v 1 2 3\n")
            missing = Path(temp_dir) / "missing.obj"
            with self.assertRaises(RuntimeError) as ctx:
                compile_item_blends.compare_bytes(actual, missing)
            self.assertIn("missing from repository", str(ctx.exception))

    def test_compare_bytes_stale_product(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            actual = Path(temp_dir) / "actual.obj"
            expected = Path(temp_dir) / "expected.obj"
            actual.write_bytes(b"v 1 2 3\n")
            expected.write_bytes(b"v 4 5 6\n")
            with self.assertRaises(RuntimeError) as ctx:
                compile_item_blends.compare_bytes(actual, expected)
            self.assertIn("compiled product is stale", str(ctx.exception))

    def test_compare_bytes_matching_product(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            actual = Path(temp_dir) / "actual.obj"
            expected = Path(temp_dir) / "expected.obj"
            actual.write_bytes(b"v 1 2 3\n")
            expected.write_bytes(b"v 1 2 3\n")
            # Should not raise
            compile_item_blends.compare_bytes(actual, expected)


if __name__ == "__main__":
    unittest.main()
