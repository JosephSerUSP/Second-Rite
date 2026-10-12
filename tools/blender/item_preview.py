"""Quick workbench render of an item source from several angles (runs inside Blender).

    python tools/blender/run.py tools/blender/item_preview.py --blend X.blend -- OUT.png [--hide-guides]

A fast look at the SOURCE (live modifiers, cutters, Geometry Nodes) without the
OBJ compile or the LOVE round trip. It is a debugging aid, not review evidence:
the real item viewer (tools/asset-production/item_review.py) is the arbiter, and
this uses Blender's lighting, not the game's.
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0]
hide_guides = "--hide-guides" in argv
roots = [o for o in bpy.context.scene.objects if o.get("item_export")]
root = roots[0]
parts = [o for o in root.children_recursive if o.type in {"MESH", "CURVE", "META"} and not (hide_guides and o.hide_render)]
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in parts:
    for c in o.bound_box:
        pts.append(o.matrix_world @ Vector(c))
lo = Vector((min(p[i] for p in pts) for i in range(3)))
hi = Vector((max(p[i] for p in pts) for i in range(3)))
center, size = (lo + hi) / 2, max((hi - lo))
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = False
scene.render.resolution_x = scene.render.resolution_y = 384
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.1, 0.1, 0.12)
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = size * 1.25
cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
for o in bpy.data.objects:
    if o.hide_render and o.type == "MESH" and not hide_guides:
        o.hide_render = False   # show cutters/guides in wire in this debug view
        o.display_type = "WIRE"
views = [(0, 0), (60, 15), (90, 0), (30, 55)]   # (yaw around Z in degrees from front, elevation)
paths = []
for i, (yaw, elev) in enumerate(views):
    a, e = math.radians(yaw), math.radians(elev)
    direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = center + direction * size * 3
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{out}.{i}.png"
    bpy.ops.render.render(write_still=True)
    paths.append(scene.render.filepath)
print("PREVIEW", paths)
