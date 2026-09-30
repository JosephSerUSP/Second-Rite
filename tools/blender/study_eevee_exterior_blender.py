"""Blender side of study_eevee_exterior.py: the Praça atlas baked by Cycles today and by EEVEE projection.

Opens the modelled exterior source, rebuilds its joined render mesh exactly as
`export_exterior_environment.py` does, lights it as that exporter does (a world fill, one more sun, and
whatever the document already holds), and produces two atlases on the SAME mesh and UVs:

  * the Cycles one, through the exporter's own pipeline (`flat_bake`: one sample, no bounces);
  * the EEVEE one, by camera projection (`eevee_projection.py`).

Then renders, from lane positions the EEVEE bake did not use, the EEVEE beauty of the source meshes and
the joined mesh wearing each atlas, unlit and nearest-sampled at native size, as the game would draw it.
The source document is never saved. Run through `study_eevee_exterior.py`.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import atlas_allocation  # noqa: E402
import eevee_projection as projection  # noqa: E402
import export_exterior_environment as exterior  # noqa: E402
import stage_room_model as stager  # noqa: E402
import town_environment_pipeline as pipeline  # noqa: E402
from atlas_allocation import triangle_mask  # noqa: E402

DEFAULT_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments"
                 / "st_maria_praca_modelled.blend")


def place_camera(scene, lane_y):
    """Exterior sources are in engine space already: no mirror (see export_exterior_environment.py)."""
    return atlas_allocation.lane_camera(scene, lane_y, mirrored=False)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, default=DEFAULT_BLEND)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--span", type=float, default=23.699)
    parser.add_argument("--margin", type=float, default=6.0)
    parser.add_argument("--ground-share", type=float, default=0.03)
    parser.add_argument("--cull-samples", type=int, default=24)
    parser.add_argument("--cull-escape", type=float, default=0.0)
    parser.add_argument("--atlas-size", type=int, default=2048)
    parser.add_argument("--ambient", type=float, default=0.35)
    parser.add_argument("--sun", type=float, default=2.5)
    parser.add_argument("--bake-cameras", type=int, default=16)
    parser.add_argument("--supersample", type=int, default=3)
    parser.add_argument("--exposure", type=float, default=0.0, metavar="EV",
                        help="gain, in EV, on the EEVEE beauty before it goes into the atlas and on the EEVEE target")
    parser.add_argument("--probe-volume", type=float, default=0.0, metavar="CELLS_PER_M")
    parser.add_argument("--eevee-option", action="append", default=[], metavar="NAME=VALUE")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    scene = bpy.context.scene
    source = bpy.data.collections["TH_SOURCE"]
    exterior.rebuild_render_mesh(args.span, args.margin, args.ground_share,
                                 args.cull_samples, args.cull_escape)
    target = next(o for o in bpy.data.collections["TH_RENDER"].all_objects if o and o.type == "MESH")
    triangles = len(target.data.loop_triangles)

    # The same lighting the exporter stages, on top of whatever lights the document already holds.
    before = sorted((o.name, o.data.type, round(o.data.energy, 3)) for o in scene.objects if o.type == "LIGHT")
    stager.base_lighting(args.ambient, (0.0, 0.0, 0.0), stager.INTERIOR_FILL)
    stager.outdoor_sun(args.sun)
    lights = sorted((o.name, o.data.type, round(o.data.energy, 3)) for o in scene.objects if o.type == "LIGHT")
    print("lights in the document: " + json.dumps(before) + "\nlights after staging: " + json.dumps(lights), flush=True)

    # What the beauty frame sees is the source meshes that were joined; what the UV frame sees is the
    # joined mesh. Everything else in the document (guides, scale actors, preview rigs, anchors) is out.
    def square_member(obj):
        if obj.type != "MESH" or obj.hide_render or not exterior.is_bake_source(obj):
            return False
        return exterior.in_square(exterior.evaluated(obj)[0] if exterior.live_modifiers(obj) else obj,
                                  args.span, args.margin)

    for name in ("TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_COLLISION", "TH_ANCHORS", "TH_CAMERA_PREVIEW"):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_render = True
            for obj in col.all_objects:
                if obj:
                    obj.hide_render = True
    source.hide_render = False
    everything = [o for o in source.all_objects if o]      # a collection can hold an empty slot
    members = [o for o in everything if square_member(o)]
    others = [o for o in everything if o.type == "MESH" and o not in members]
    print(f"beauty frame sees {len(members)} source meshes; {len(others)} others are out", flush=True)

    def beauty_pass():
        target.hide_render = True
        for obj in members:
            obj.hide_render = False
        for obj in others:
            obj.hide_render = True

    def unlit_pass():
        target.hide_render = False
        for obj in members + others:
            obj.hide_render = True

    scene.render.engine = "BLENDER_EEVEE"
    if args.eevee_option:
        print("eevee options: " + json.dumps(stager.apply_eevee_options(scene.eevee, args.eevee_option)), flush=True)
    probe = None
    if args.probe_volume > 0:
        beauty_pass()
        probe = stager.add_probe_volume(scene, args.probe_volume, 256)
        print("probe volume: " + json.dumps(probe), flush=True)

    size = args.atlas_size
    lo, hi = 0.6, args.span - 0.6
    positions = list(np.linspace(lo, hi, args.bake_cameras))
    step = (hi - lo) / (args.bake_cameras - 1)
    # Held-out: between bake cameras, and the two ends of the walkable lane.
    checks = [lo + step * 0.5, (lo + hi) / 2 + step * 0.5, hi - step * 0.5, 0.35, args.span - 0.35]

    started = time.time()
    projected = projection.project_atlas(scene, target.data.uv_layers.active.name, positions, place_camera,
                                         size, out, supersample=args.supersample, exposure=args.exposure,
                                         beauty_pass=beauty_pass, uv_pass=unlit_pass,
                                         log=lambda line: print(line, flush=True))
    eevee_atlas, coverage = projection.finish_atlas(projected, triangle_mask(target.data, size),
                                                    "SR_EEVEE_ATLAS", out / "atlas_eevee.png")
    eevee_seconds = time.time() - started
    print(f"EEVEE atlas: {json.dumps(coverage)} in {eevee_seconds:.1f}s", flush=True)

    # -- judge it from lane positions the bake did not use -------------------------------------
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    projection.crisp(scene)

    def frames(label, image=None):
        for number, lane_y in enumerate(checks):
            place_camera(scene, float(lane_y))
            scene.render.engine = "BLENDER_EEVEE"
            if image is None:
                beauty_pass()
                bpy.context.view_layer.material_override = None
                scene.view_settings.exposure = args.exposure
            else:
                unlit_pass()
                bpy.context.view_layer.material_override = projection.atlas_material(image)
                scene.view_settings.exposure = 0.0     # the EEVEE gain is already in the atlas texels
            scene.render.filepath = str(out / f"{label}_{number}.png")
            bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.material_override = None
        scene.view_settings.exposure = 0.0

    frames("target_eevee")
    frames("atlas_eevee", eevee_atlas)

    density = []
    unlit_pass()
    for lane_y in checks:
        place_camera(scene, float(lane_y))
        bpy.context.view_layer.material_override = projection.uv_material(target.data.uv_layers.active.name)
        scene.eevee.taa_render_samples = 1
        scene.render.filter_size = 0.0
        projection.set_raw_float_output(scene, out / "tmp_uv.exr", 1)
        density.append(projection.texel_density(projection.render_exr(scene, out / "tmp_uv.exr"), size))
        bpy.context.view_layer.material_override = None
    (out / "tmp_uv.exr").unlink(missing_ok=True)
    density = np.concatenate(density)
    density_report = {"pixelsMeasured": int(density.size), "p10": round(float(np.percentile(density, 10)), 3),
                      "median": round(float(np.median(density)), 3), "p90": round(float(np.percentile(density, 90)), 3),
                      "fractionBelowOne": round(float((density < 1.0).mean()), 4)}
    print("texels per screen pixel: " + json.dumps(density_report), flush=True)

    # -- the Cycles atlas, through the exporter's own pipeline, on the same mesh ----------------
    started = time.time()
    pipeline.run_pipeline_in_blender(args.blend.resolve(), out / "cycles_package", atlas_size=size,
                                     bake_samples=24, flat_bake=True)
    cycles_seconds = time.time() - started
    cycles_atlas = bpy.data.images.load(str(out / "cycles_package" / "environment.png"))
    cycles_atlas.colorspace_settings.name = "sRGB"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.resolution_x, scene.render.resolution_y = projection.VIEW_WIDTH, projection.VIEW_HEIGHT
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    projection.crisp(scene)
    frames("atlas_cycles", cycles_atlas)

    def mean_lit(image):
        pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
        lit = pixels.max(axis=1) > 0
        return round(float(projection.srgb_encode(pixels[lit]).mean() * 255.0), 2) if lit.any() else 0.0

    result = {"blend": args.blend.name, "atlasSize": size, "triangles": triangles,
              "lightsInDocument": before, "lightsAfterStaging": lights, "lampsWorld": args.ambient, "sun": args.sun,
              "sourceMeshesSeenByBeauty": len(members), "bakeCameras": projected["cameras"],
              "checkCameras": [round(float(y), 3) for y in checks], "probeVolume": probe,
              "exposureEV": args.exposure, "eeveeCoverage": coverage, "texelsPerPixel": density_report,
              "eeveeBakeSeconds": round(eevee_seconds, 1), "cyclesBakeSeconds": round(cycles_seconds, 1),
              "atlasMeanWrittenTexel": {"eevee": mean_lit(eevee_atlas), "cycles": mean_lit(cycles_atlas)}}
    (out / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("EEVEE EXTERIOR STUDY OK", out)


if __name__ == "__main__":
    main()
