"""Blender side of test_ground_cover_adoption.py: describe a document, and what its cover realises.

    blender -b --factory-startup -P adoption_blender.py -- DOCUMENT.blend

Prints one `ADOPTION_PROBE {json}` line: a census of every datablock (with a hash of each mesh's
vertices, so a touched mesh shows), and, if the document carries the cover, what it realises.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import ground_cover  # noqa: E402
import ground_cover_placement as placement  # noqa: E402


def mesh_hash(mesh):
    digest = hashlib.sha256()
    for vertex in mesh.vertices:
        digest.update(("%.5f,%.5f,%.5f;" % tuple(vertex.co)).encode())
    digest.update(str(len(mesh.polygons)).encode())
    return digest.hexdigest()[:16]


def census():
    scene = bpy.context.scene
    return {
        "objects": {o.name: [o.type, [round(v, 5) for v in o.matrix_world.translation],
                             [c.name for c in o.users_collection], bool(o.hide_render)]
                    for o in bpy.data.objects},
        "meshes": {m.name: mesh_hash(m) for m in bpy.data.meshes},
        "materials": sorted(m.name for m in bpy.data.materials),
        "node_groups": sorted(g.name for g in bpy.data.node_groups),
        "collections": {c.name: sorted(o.name for o in c.objects) for c in bpy.data.collections},
        # Render Result and Viewer Node are images Blender makes on its own; they are never authored data.
        "images": sorted(i.name for i in bpy.data.images if i.type not in ("RENDER_RESULT", "COMPOSITING")),
        "cameras": {c.name: [c.lens, c.shift_y] for c in bpy.data.cameras},
        "lights": sorted(l.name for l in bpy.data.lights),
        "worlds": sorted(w.name for w in bpy.data.worlds),
        "scene": {"camera": scene.camera.name if scene.camera else None, "engine": scene.render.engine,
                  "resolution": [scene.render.resolution_x, scene.render.resolution_y]},
    }


def realised():
    host = bpy.data.objects.get(ground_cover.HOST_NAME)
    if host is None:
        return None
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lane = bpy.data.objects["LD_walkable_lane_0.0_to_23.699"]
    corners = [lane.matrix_world @ Vector(c) for c in lane.bound_box]
    x_lo, x_hi = min(c.x for c in corners), max(c.x for c in corners)
    y_lo, y_hi = min(c.y for c in corners), max(c.y for c in corners)
    bases = placement.tufts(host)
    under_building = in_lane = out_of_frame = above_menu = 0
    for x, y, z in bases:
        hit, _l, _n, _i, obj, _m = scene.ray_cast(depsgraph, Vector((x, y, z + 12.0)), Vector((0, 0, -1)))
        if hit and placement._is_building_or_roof(obj):
            under_building += 1
        if x_lo <= x <= x_hi and y_lo <= y <= y_hi:
            in_lane += 1
        ndc = world_to_camera_view(scene, scene.camera, Vector((x, y, z)))
        px, py = ndc.x * placement.PLATE[0], (1.0 - ndc.y) * placement.PLATE[1]
        if not (0 <= px <= placement.PLATE[0] and 0 <= py <= placement.PLATE[1]):
            out_of_frame += 1
        elif py < placement.MENU_TOP_ROW:
            above_menu += 1
    modifier = host.modifiers[ground_cover.GROUP_NAME]
    inputs = {i.name: getattr(modifier.properties.inputs, i.identifier).value
              for i in modifier.node_group.interface.items_tree
              if getattr(i, "in_out", None) == "INPUT" and i.socket_type in ("NodeSocketFloat", "NodeSocketInt")}
    return {"tufts": len(bases), "underBuilding": under_building, "inLane": in_lane,
            "outOfFrame": out_of_frame, "aboveMenu": above_menu, "maxTufts": inputs.get("Max Tufts"),
            "bake": bool(host.get(ground_cover.BAKE_PROPERTY)),
            "inSource": host.name in bpy.data.collections["TH_SOURCE"].all_objects,
            "properties": {k: host.get(k) for k in ("sr_cover_layout", "sr_cover_budget", "sr_cover_seed")}}


def main():
    document = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.open_mainfile(filepath=document)
    print("ADOPTION_PROBE " + json.dumps({"census": census(), "realised": realised()}))


if __name__ == "__main__":
    main()
