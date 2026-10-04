"""Pinned-Blender worker for furnishings_catalogue.py; never saves a .blend."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "recipes")]
import furnishings_catalogue as catalogue
import interior
import furnishings
from furnishing_geometry import bounds as measure


PALETTE = {m["id"]: m for m in json.loads(
    (catalogue.ROOT / "tools/asset-language/materials.json").read_text(encoding="utf-8"))["materials"]}


def flat_material(semantic_id):
    mat = bpy.data.materials.get(semantic_id) or bpy.data.materials.new(semantic_id)
    mat.diffuse_color = (*[v/255 for v in PALETTE[semantic_id]["baseColorSrgb"]], 1)
    return mat


def build_entry(api, output):
    # This replaces material binding only inside an unsaved preview scene.
    # All shapes, joins and defaults execute the production builders.
    interior.material = flat_material
    room = interior.Interior("catalogue_preview", half_width=3, depth=6, ceiling_z=3.7)
    room.openings = [(-.55, .55, 0, 2.2)] if api["id"] == "azulejo_dado" else []
    kwargs = {"room": room}
    for p in api["parameters"]:
        if p["name"] == "name":
            kwargs["name"] = api["id"]
        elif p["name"] == "at":
            kwargs["at"] = (0, 0)
    for name, value in api["fixture"].items():
        kwargs[name] = flat_material(value["material"]) if isinstance(value, dict) else value
    getattr(furnishings, api["id"])(**kwargs)
    room.finish()
    parts = list(room.parts)
    bounds = measure(parts)
    lo, hi = bounds
    api.update(bounds=bounds, dimensions=[round(b-a, 6) for a,b in zip(lo,hi)],
               materials=sorted({m.name for o in parts if o.type == "MESH" for m in o.data.materials if m}),
               meshCount=sum(o.type == "MESH" for o in parts), lightCount=sum(o.type == "LIGHT" for o in parts))
    centre = Vector([(a+b)/2 for a,b in zip(lo, hi)])
    span = max(api["dimensions"])
    # A faint backing identifies wall-dependent fixtures; it never enters bounds.
    if api["id"] in {"shelf", "lantern", "azulejo_dado", "window_dressing", "tool_rail", "framed_picture"}:
        context = bpy.data.materials.new("preview_context")
        context.diffuse_color = (.77, .77, .75, 1)
        room.part("preview_wall_context", (.02, max(hi[1]-lo[1], 1)*1.1, max(hi[2]-lo[2], 1)*1.1),
                  (hi[0]+.035, centre.y, centre.z), context)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 256, 224
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_specular_highlight = False
    shading.background_type = "WORLD"
    scene.world.color = (.80, .79, .76)
    scene.view_settings.view_transform = "Standard"
    scene.display.render_aa = "16"
    camera_data = bpy.data.cameras.new("catalogue_camera")
    camera = bpy.data.objects.new("catalogue_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = centre + Vector((-6, -5, 3.5)).normalized() * max(span*3, 2)
    camera.rotation_euler = (centre-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    # Project actual corners into camera axes, so long runners and tall frames fit.
    rotation = camera.rotation_euler.to_matrix().transposed()
    corners = [rotation @ (Vector((x,y,z))-centre) for x in (lo[0],hi[0])
               for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
    camera_data.ortho_scale = max(max(v.x for v in corners)-min(v.x for v in corners),
                                  (max(v.y for v in corners)-min(v.y for v in corners))*256/224)*1.2
    scene.camera = camera
    scene.render.filepath = str(output / f"{api['id']}.png")
    bpy.ops.render.render(write_still=True)
    print(f"CATALOGUE {api['id']}: {api['dimensions']}", flush=True)
    return api


if __name__ == "__main__":
    output = Path(sys.argv[sys.argv.index("--")+1]).resolve()
    rows = [build_entry(api, output) for api in catalogue.inventory()]
    (output / "measurements.json").write_text(json.dumps(rows, indent=2)+"\n", encoding="utf-8")
