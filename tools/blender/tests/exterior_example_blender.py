"""Blender side of test_exterior_example: build the worked exterior, measure it,
then break it on purpose and measure again."""
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "blender"), str(ROOT / "tools" / "blender" / "recipes"),
                str(ROOT / "tools" / "blender" / "recipes" / "examples")]
import exterior_reference as example  # noqa: E402

probe = {}
ext = example.build()
bpy.context.view_layer.update()
probe["clean"], probe["cleanProblems"] = example.measure(ext)
probe["rootNames"] = sorted(o.name for o in bpy.data.objects if o.parent is None
                            and o.type == "EMPTY")

# Negative control 1: a tall, wide panel in the pass-behind rank is a BOARD.
ext.foreground("injected_board", 12.0, size=(0.3, 3.0, 3.0), x=-5.0)
bpy.context.view_layer.update()
_, probe["boardProblems"] = example.measure(ext)

# Negative control 2: saving the example into a Project is refused.
try:
    example.save(ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring"
                 / "environments" / "example_exterior_reference.blend")
    probe["projectSaveRefused"] = False
except SystemExit:
    probe["projectSaveRefused"] = True

print("EXTERIOR_EXAMPLE_PROBE " + json.dumps(probe, sort_keys=True))
