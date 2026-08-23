"""The standalone item compile must validate its own OBJ product.

``compile_item_blends.py`` (the host-side batch entry point) validates every
product it creates. ``compile_item_blend.py`` runs *inside* Blender and its
docstring documents a standalone invocation that bypasses that host wrapper
entirely, so it has to carry the same check itself.

These tests are static because ``compile_item_blend.py`` imports ``bpy`` at
module scope and cannot be imported by plain CPython. The analysis is expressed
as a reusable function so the negative controls can run it against deliberately
broken copies of the source -- a test that only ever sees the healthy file
cannot show that it would notice the guard disappearing.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLENDER_TOOLS = ROOT / "tools" / "blender"
COMPILE_SCRIPT = BLENDER_TOOLS / "compile_item_blend.py"

if str(BLENDER_TOOLS) not in sys.path:
    sys.path.insert(0, str(BLENDER_TOOLS))

from validate_item_obj_runtime import validate

VALIDATOR_MODULE = "validate_item_obj_runtime"


def _imported_validator_names(tree: ast.Module) -> set[str]:
    """Local names bound to validate_item_obj_runtime.validate."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == VALIDATOR_MODULE:
            for alias in node.names:
                if alias.name == "validate":
                    names.add(alias.asname or alias.name)
    return names


def _function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_lines(scope: ast.AST, callee_names: set[str]) -> list[int]:
    """Line numbers of calls to any bare name in callee_names."""
    lines = []
    for node in ast.walk(scope):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in callee_names:
                lines.append(node.lineno)
    return sorted(lines)


def analyse(source: str) -> dict:
    """Report how the compile script guards its exported product."""
    tree = ast.parse(source)
    validators = _imported_validator_names(tree)
    main = _function(tree, "main")
    validate_lines = _call_lines(main, validators) if main and validators else []
    inject_lines = _call_lines(main, {"inject_runtime_passes"}) if main else []
    return {
        "imports_validator": bool(validators),
        "validates_in_main": bool(validate_lines),
        "validate_line": validate_lines[0] if validate_lines else None,
        "inject_line": inject_lines[0] if inject_lines else None,
    }


class CompileItemBlendValidationTests(unittest.TestCase):
    def setUp(self):
        self.source = COMPILE_SCRIPT.read_text(encoding="utf-8")
        self.report = analyse(self.source)

    def test_imports_the_shared_runtime_validator(self):
        # The same validator the batch path uses -- not a second implementation.
        self.assertTrue(
            self.report["imports_validator"],
            f"compile_item_blend.py must import validate from {VALIDATOR_MODULE}",
        )

    def test_validates_the_exported_product_in_main(self):
        self.assertTrue(
            self.report["validates_in_main"],
            "compile_item_blend.py must validate the OBJ it exported before reporting success",
        )

    def test_validation_runs_after_the_mtl_injection(self):
        # The validator resolves `mtllib` against the product directory, so it
        # can only pass once inject_runtime_passes has written that MTL.
        self.assertIsNotNone(self.report["inject_line"])
        self.assertIsNotNone(self.report["validate_line"])
        self.assertGreater(
            self.report["validate_line"],
            self.report["inject_line"],
            "validation must follow the MTL injection so mtllib resolves",
        )

    # -- negative controls: the analysis must fail on a source missing the guard

    def test_analysis_rejects_a_source_with_the_validate_call_removed(self):
        # Neutralised rather than deleted: dropping the line would empty the
        # enclosing try block and the mutation would fail to parse, which would
        # pass this test for the wrong reason.
        broken = self.source.replace("validate_runtime_obj(output_path)", "pass", 1)
        self.assertNotEqual(broken, self.source)
        self.assertFalse(analyse(broken)["validates_in_main"])

    def test_analysis_rejects_a_source_that_never_imports_the_validator(self):
        broken = "\n".join(
            line for line in self.source.splitlines()
            if f"from {VALIDATOR_MODULE} import" not in line
        )
        self.assertFalse(analyse(broken)["imports_validator"])

    def test_analysis_rejects_validation_placed_before_the_mtl_injection(self):
        broken = self.source.replace(
            "    if material_passes:\n",
            "    validate_runtime_obj(output_path)\n    if material_passes:\n",
            1,
        )
        report = analyse(broken)
        self.assertLess(report["validate_line"], report["inject_line"])


class GuardRejectsRealDegenerateGeometryTests(unittest.TestCase):
    """The imported guard is the one that actually refuses a bad product."""

    def test_collinear_triangle_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "item.obj"
            path.write_text("v 0 0 0\nv 1 0 0\nv 2 0 0\nf 1 2 3\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "degenerate face"):
                validate(path)

    def test_second_fan_triangle_of_a_quad_is_checked(self):
        # The runtime fans an n-gon from its first corner, so the trailing
        # triangles matter as much as the leading one.
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "item.obj"
            path.write_text(
                "v 0 0 0\nv 1 0 0\nv 2 0 0\nv 3 0 0\nf 1 2 3 4\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "degenerate face"):
                validate(path)

    def test_sound_mesh_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "item.obj"
            path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
            self.assertEqual(validate(path)["triangles"], 1)


if __name__ == "__main__":
    unittest.main()
