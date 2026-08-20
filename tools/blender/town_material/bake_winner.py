"""Phase 6/9: bake the winner's beauty atlas and export the runtime package.

    TH_SOURCE (rich, displaced, lit)  --bake-->  ONE atlas on coarse TH_RENDER

The bake is COMBINED, so the Blender lighting is baked in: that is the whole
point of a pre-rendered-style town. Preview actors are excluded, collision and
anchors stay separate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import bpy  # noqa: E402

import thestra_camera  # noqa: E402
import town_builder as TB  # noqa: E402
import town_assembly as TA  # noqa: E402
from town_attempts import ATTEMPTS  # noqa: E402

ROOT = HERE.parents[2]
EXPORT = ROOT / "exports/environments/town_next"


def join_collection(name, new_name):
    obs = [o for o in bpy.data.collections[name].objects if o.type == "MESH"]
    for o in obs:
        o.hide_render = False
        o.hide_set(False)
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = new_name
    return joined


def tri_count_of(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--calibration", required=True, type=Path)
    ap.add_argument("--atlas", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--blend", type=Path, default=None)
    ap.add_argument("--census", type=Path, default=None)
    ap.add_argument("--source-render", type=Path, default=None)
    ap.add_argument("--baked-render", type=Path, default=None)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = ap.parse_args(argv)

    spec = ATTEMPTS[args.attempt]
    record = json.loads(args.calibration.read_text(encoding="utf-8"))
    scene = TB.reset_scene()
    scene.cycles.samples = args.samples
    cam = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
    TB.put(cam, "TH_CAMERA_PREVIEW")
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"
    TB.light_rig(scene, spec["lighting"])
    census = TA.build_town(scene, spec)
    actors = TB.place_actors(scene, cam, spec)

    # ---------- A. rich source render (actors visible, runtime hidden)
    for c in ("TH_RENDER", "TH_COLLISION", "TH_ANCHORS"):
        for o in bpy.data.collections[c].objects:
            o.hide_render = True
    src_tris = sum(1 for _ in ())  # placeholder, computed below
    dg = bpy.context.evaluated_depsgraph_get()
    src_tris = 0
    for o in bpy.data.collections["TH_SOURCE"].objects:
        if o.type == "MESH":
            src_tris += tri_count_of(o)
    if args.source_render:
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(args.source_render)
        bpy.ops.render.render(write_still=True)

    # ---------- B. bake TH_SOURCE onto joined TH_RENDER
    # actors must never leak into the environment bake
    for a in actors:
        a.hide_render = True

    target = join_collection("TH_RENDER", "TOWN_RENDER")
    target.hide_render = False
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")

    img = bpy.data.images.new("town_atlas", args.atlas, args.atlas, alpha=False)
    mat = bpy.data.materials.new("TOWN_BAKED")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    nt.nodes.active = tex
    target.data.materials.clear()
    target.data.materials.append(mat)

    sources = [o for o in bpy.data.collections["TH_SOURCE"].objects if o.type == "MESH"]
    for o in sources:
        o.hide_render = False
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target

    scene.cycles.bake_type = "COMBINED"
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.6
    scene.render.bake.max_ray_distance = 1.2
    scene.render.bake.margin = 6
    scene.render.bake.use_clear = True
    bpy.ops.object.bake(type="COMBINED")

    EXPORT.mkdir(parents=True, exist_ok=True)
    atlas_path = EXPORT / "environment.png"
    img.filepath_raw = str(atlas_path)
    img.file_format = "PNG"
    img.save()

    rnd_tris = tri_count_of(target)

    # ---------- C. baked render through the same camera
    for o in sources:
        o.hide_render = True
    target.hide_render = False
    if args.baked_render:
        scene.render.filepath = str(args.baked_render)
        bpy.ops.render.render(write_still=True)

    # ---------- D. export runtime package
    for o in bpy.data.objects:
        o.select_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.wm.obj_export(filepath=str(EXPORT / "environment.obj"),
                          export_selected_objects=True, export_materials=True,
                          export_uv=True, export_normals=True, forward_axis="Y",
                          up_axis="Z")

    coll = [o for o in bpy.data.collections["TH_COLLISION"].objects if o.type == "MESH"]
    if coll:
        for o in bpy.data.objects:
            o.select_set(False)
        for o in coll:
            o.hide_render = False
            o.select_set(True)
        bpy.context.view_layer.objects.active = coll[0]
        bpy.ops.wm.obj_export(filepath=str(EXPORT / "collision.obj"),
                              export_selected_objects=True, export_materials=False,
                              export_uv=False, forward_axis="Y", up_axis="Z")

    anchors = [{"name": o.name, "kind": o.get("thestra_anchor"),
                "position": [round(v, 4) for v in o.location]}
               for o in bpy.data.collections["TH_ANCHORS"].objects]

    src_mats = sorted({m.get("th_source_id") for o in sources
                       for m in o.data.materials if m and m.get("th_source_id")})
    strategies = {}
    for sid in src_mats:
        strategies.setdefault(sid.split(":")[0], []).append(sid)

    env = {
        "contract": "second-gate.baked-environment",
        "version": 1,
        "attempt": args.attempt,
        "title": spec["title"],
        "camera": {"lensMm": round(float(cam.data.lens), 4),
                   "eye": [round(v, 6) for v in cam.location],
                   "pitchDegrees": 0.0,
                   "targetWidth": record["targetWidth"],
                   "targetHeight": record["targetHeight"]},
        "atlas": {"file": "environment.png", "width": args.atlas, "height": args.atlas},
        "mesh": {"file": "environment.obj", "triangles": rnd_tris},
        "collision": {"file": "collision.obj", "objects": len(coll)},
        "anchors": anchors,
        "sourceMaterials": src_mats,
        "materialStrategies": {k: len(v) for k, v in strategies.items()},
        "note": ("Runtime receives coarse geometry, one baked beauty atlas, "
                 "collision and anchors. No Blender material graph is a runtime "
                 "dependency, and no preview actor is baked in."),
    }
    (EXPORT / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")

    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        # keep the rich source in the .blend
        for o in sources:
            o.hide_render = False
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))

    census.update({"attempt": args.attempt, "sourceTris": src_tris,
                   "renderTris": rnd_tris,
                   "reductionRatio": round(src_tris / max(rnd_tris, 1), 2),
                   "atlas": args.atlas, "sourceMaterials": src_mats,
                   "materialStrategies": env["materialStrategies"]})
    if args.census:
        args.census.write_text(json.dumps(census, indent=2), encoding="utf-8")
    print("BAKE_OK " + json.dumps(census))


if __name__ == "__main__":
    main()
