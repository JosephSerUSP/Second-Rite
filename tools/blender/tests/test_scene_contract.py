"""Focused, Blender-independent tests for the town scene contract preflight."""

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
TOOLS = ROOT / "tools" / "blender"
sys.path.insert(0, str(TOOLS))

from scene_contract import inspect_snapshot


IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def obj(name, object_type, collections, *, matrix=None, mesh=None):
    record = {"name": name, "type": object_type, "collections": collections,
              "matrix_world": IDENTITY if matrix is None else matrix}
    if mesh is not None:
        record["mesh"] = mesh
    return record


def good_snapshot():
    return {
        "collections": [{"name": name} for name in (
            "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
            "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW")],
        "objects": [
            obj("anything", "MESH", ["TH_SOURCE"]),
            obj("also_anything", "MESH", ["TH_RENDER"],
                mesh={"vertexCount": 8, "polygonCount": 6, "uvLayerCount": 1}),
            obj("optional_blocker", "MESH", ["TH_COLLISION"]),
            obj("spawn", "EMPTY", ["TH_ANCHORS"]),
            obj("GUIDE_named_only", "MESH", ["TH_PREVIEW_ONLY"]),
            obj("preview", "MESH", ["TH_PREVIEW_ACTORS"]),
            obj("camera", "CAMERA", ["TH_CAMERA_PREVIEW"]),
        ],
    }


class SceneContractTests(unittest.TestCase):
    def test_good_scene_passes_and_names_do_not_assign_roles(self):
        report = inspect_snapshot(good_snapshot())
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["errorCount"], 0)
        self.assertEqual(report["collections"]["TH_RENDER"]["types"], {"MESH": 1})
        self.assertEqual([item["name"] for item in report["anchors"]], ["spawn"])
        guide = next(item for item in report["objects"] if item["name"] == "GUIDE_named_only")
        self.assertEqual(guide["roles"], ["TH_PREVIEW_ONLY"])
        self.assertEqual(report["semantics"]["objectNames"], "labels_only")

    def test_missing_and_empty_required_roles_are_actionable(self):
        snapshot = {"collections": [{"name": "TH_SOURCE"}, {"name": "TH_RENDER"}],
                    "objects": [obj("source", "MESH", ["TH_SOURCE"])]}
        report = inspect_snapshot(snapshot)
        codes = {item["code"] for item in report["diagnostics"]}
        self.assertIn("missing_role", codes)
        self.assertIn("empty_role", codes)
        self.assertIn("TH_RENDER", {item.get("role") for item in report["diagnostics"]})

    def test_ambiguous_membership_and_guide_leakage_fail(self):
        snapshot = good_snapshot()
        snapshot["objects"].extend([
            obj("shared", "MESH", ["TH_SOURCE", "TH_RENDER"]),
            obj("leaked_guide", "MESH", ["TH_RENDER", "TH_PREVIEW_ONLY"]),
        ])
        report = inspect_snapshot(snapshot)
        codes = {item["code"] for item in report["diagnostics"]}
        self.assertIn("ambiguous_role", codes)
        self.assertIn("guide_leakage", codes)

    def test_invalid_transform_and_unsupported_input_fail(self):
        snapshot = good_snapshot()
        snapshot["objects"].extend([
            obj("bad_anchor", "MESH", ["TH_ANCHORS"]),
            obj("nan_source", "MESH", ["TH_SOURCE"],
                matrix=[[1, 0, 0, 0], [0, float("nan"), 0, 0],
                        [0, 0, 1, 0], [0, 0, 0, 1]]),
            obj("singular_render", "MESH", ["TH_RENDER"],
                matrix=[[0, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]),
        ])
        report = inspect_snapshot(snapshot)
        diagnostics = report["diagnostics"]
        self.assertTrue(any(item["code"] == "unsupported_input" and
                            item.get("object") == "bad_anchor" for item in diagnostics))
        self.assertTrue(any(item["code"] == "invalid_transform" and
                            item.get("object") == "nan_source" for item in diagnostics))
        self.assertTrue(any(item["code"] == "invalid_transform" and
                            item.get("object") == "singular_render" for item in diagnostics))

    def test_source_requires_bakeable_geometry_not_only_lights(self):
        snapshot = good_snapshot()
        snapshot["objects"] = [item for item in snapshot["objects"]
                                if "TH_SOURCE" not in item["collections"]]
        snapshot["objects"].append(obj("source_light", "LIGHT", ["TH_SOURCE"]))
        report = inspect_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertTrue(any(item["code"] == "missing_source_geometry"
                            for item in report["diagnostics"]))

    def test_malformed_public_snapshot_boundary_is_structured(self):
        malformed = good_snapshot()
        malformed["objects"][0]["collections"] = None
        malformed["objects"][1]["collections"] = [["TH_RENDER"]]
        report = inspect_snapshot(malformed)
        self.assertFalse(report["ok"])
        codes = {item["code"] for item in report["diagnostics"]}
        self.assertIn("malformed_memberships", codes)
        self.assertIn("malformed_membership", codes)

        report = inspect_snapshot(None)
        self.assertFalse(report["ok"])
        self.assertEqual(report["diagnostics"][0]["code"], "malformed_snapshot")

    def test_malformed_collections_are_structured(self):
        report = inspect_snapshot({"collections": None, "objects": []})
        self.assertFalse(report["ok"])
        self.assertEqual(report["diagnostics"][0]["code"], "malformed_collections")
        report = inspect_snapshot({"collections": [{"name": None}], "objects": []})
        self.assertFalse(report["ok"])
        self.assertIn("malformed_collection", {item["code"] for item in report["diagnostics"]})

    def test_collision_is_optional_and_does_not_claim_walkability(self):
        snapshot = good_snapshot()
        snapshot["collections"] = [item for item in snapshot["collections"]
                                    if item["name"] != "TH_COLLISION"]
        snapshot["objects"] = [item for item in snapshot["objects"]
                                if "TH_COLLISION" not in item["collections"]]
        report = inspect_snapshot(snapshot)
        self.assertTrue(report["ok"])
        self.assertFalse(report["collections"]["TH_COLLISION"]["present"])
        self.assertIn("does_not_claim_walkability", report["semantics"]["collision"])

    def test_cli_writes_versioned_machine_readable_report_and_strict_fails(self):
        with tempfile.TemporaryDirectory(prefix="scene_contract_test_") as directory:
            root = Path(directory)
            snapshot_path = root / "scene.json"
            report_path = root / "report.json"
            snapshot_path.write_text(json.dumps({"collections": [], "objects": []}),
                                     encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TOOLS / "scene_contract.py"),
                 "--snapshot", str(snapshot_path), "--output", str(report_path),
                 "--strict"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "thestra.scene-contract-report")
            self.assertEqual(report["schemaVersion"], 1)
            self.assertFalse(report["ok"])
            self.assertGreater(report["summary"]["errorCount"], 0)

    def test_external_blend_strict_and_blender_script_failures_propagate(self):
        blender = os.environ.get("BLENDER") or shutil.which("blender")
        if not blender:
            blender_path = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
            if blender_path.is_file():
                blender = str(blender_path)
        if not blender:
            self.skipTest("Blender not available")

        fixture = TOOLS / "fixtures" / "town_slice_synthetic.blend"
        with tempfile.TemporaryDirectory(prefix="scene_contract_blender_") as directory:
            root = Path(directory)
            invalid_blend = root / "invalid.blend"
            create_expression = (
                "import bpy; "
                "collection = bpy.data.collections.get('TH_RENDER'); "
                "bpy.data.collections.remove(collection, do_unlink=True); "
                # Blender's embedded Python parses this expression on Windows;
                # forward slashes avoid turning a drive path into \u escapes.
                f"bpy.ops.wm.save_as_mainfile(filepath={str(invalid_blend).replace(chr(92), '/')!r})"
            )
            created = subprocess.run(
                [blender, "--background", str(fixture), "--python-expr", create_expression],
                capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)

            report_path = root / "invalid-report.json"
            wrapper_environment = os.environ.copy()
            wrapper_environment["BLENDER"] = blender
            failed_validation = subprocess.run(
                [sys.executable, str(TOOLS / "scene_contract.py"), "--blend",
                 str(invalid_blend), "--output", str(report_path), "--strict"],
                capture_output=True, text=True, env=wrapper_environment)
            self.assertNotEqual(failed_validation.returncode, 0,
                                failed_validation.stdout + failed_validation.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["ok"])
            self.assertIn("missing_role", {item["code"] for item in report["diagnostics"]})

            output_directory = root / "output-directory"
            output_directory.mkdir()
            failed_script = subprocess.run(
                [sys.executable, str(TOOLS / "scene_contract.py"), "--blend",
                 str(fixture), "--output", str(output_directory)],
                capture_output=True, text=True, env=wrapper_environment)
            self.assertNotEqual(failed_script.returncode, 0,
                                failed_script.stdout + failed_script.stderr)


if __name__ == "__main__":
    unittest.main()
