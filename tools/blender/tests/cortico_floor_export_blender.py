"""Blender-side positive/negative probe for the Cortico floor exporter."""
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import export_exterior_environment  # noqa: E402


def main():
    result = {}
    try:
        blend = Path(os.environ["CORTICO_FLOOR_TEST_BLEND"]).resolve()
        output = Path(os.environ["CORTICO_FLOOR_TEST_OUTPUT"]).resolve()
        output.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        report = export_exterior_environment.export_floor_mesh(output, bpy.context.scene)
        result["report"] = report
        result["files"] = sorted(path.name for path in output.iterdir())
        background_output = output.parent / "background"
        background_output.mkdir(parents=True, exist_ok=True)
        background = export_exterior_environment.export_background_layers(
            background_output, bpy.context.scene)
        result["background"] = background
        result["backgroundFiles"] = sorted(
            path.name for path in background_output.iterdir())
        if [layer["id"] for layer in background] != [
                "centre", "east", "laundry_quad", "west"]:
            raise RuntimeError("background export did not return canonical layer ids")
        for layer in background:
            if layer["provenance"]["cameraSpace"] is not False:
                raise RuntimeError("background layer unexpectedly uses camera space")
            if layer["provenance"]["reactsToPitch"] is not True:
                raise RuntimeError("background layer lost pitch-reactive provenance")
        grid = bpy.data.objects.get("CORTICO_floor_grid")
        if grid is None:
            raise RuntimeError("positive probe lost CORTICO_floor_grid")
        bpy.data.objects.remove(grid, do_unlink=True)
        negative = output.parent / "negative"
        negative.mkdir(parents=True, exist_ok=True)
        try:
            export_exterior_environment.export_floor_mesh(negative, bpy.context.scene)
        except RuntimeError as error:
            result["negativeError"] = str(error)
        else:
            raise RuntimeError("missing sr_floor_mesh did not fail")
        result["ok"] = True
    except Exception:
        result["ok"] = False
        result["error"] = traceback.format_exc()
    print("CORTICO_FLOOR_EXPORT_TEST " + json.dumps(result, sort_keys=True))


main()
