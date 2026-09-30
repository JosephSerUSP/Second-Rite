"""Can an atlas be baked with EEVEE? A camera-projection bake, measured against Cycles.

EEVEE has no bake (`bpy.ops.object.bake` refuses: "Current render engine does not support
baking"), and the room atlas is a Cycles selected-to-active bake. But the game never sees a
room from just anywhere: the side-view camera is fixed in pitch and distance and slides
along the lane. So a texel only has to hold what that camera can see, and that can be
captured by rendering.

For each camera position along the lane this renders two frames of the same joined room mesh
(`TH_RENDER`, the one the atlas belongs to):

  * a BEAUTY frame with EEVEE and the room's own lights and materials, in linear light;
  * a UV frame of the same mesh under an emission override that paints each pixel with its own
    (u, v), in 32-bit float with no antialiasing, so every pixel names the texel it came from.

Splatting the beauty pixels into the atlas by their UV averages every sighting of a texel, so
a texel a camera sees at higher resolution counts for more. The average is taken in linear
light and encoded to sRGB at the end, as the Cycles bake's PNG is.

To judge it the atlas is put back on the mesh as an unlit, nearest-sampled emission texture
(the way the runtime draws it) and photographed from camera positions the bake did NOT use.
The same is done with a Cycles atlas, and both are laid beside their beauty target.

    blender -b --factory-startup --python tools/blender/study_eevee_atlas.py -- \
        --blend projects/hichaukitoden-game/assets/authoring/environments/alicias_padaria.blend \
        --cycles-atlas out/atlas-drift/alicias_padaria_3d/environment.png --out out/eevee-atlas/padaria

Nothing here writes an asset; the `.blend` is opened and never saved.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import emissive_lights  # noqa: E402
import export_room_environment as exporter  # noqa: E402
import light_fixtures  # noqa: E402
import stage_room_model as stager  # noqa: E402
import atlas_allocation  # noqa: E402
from atlas_allocation import triangle_mask  # noqa: E402
import thestra_camera  # noqa: E402

CAMERA_RECORD = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"
from eevee_projection import (  # noqa: E402
    atlas_material, crisp, dilate, finish_atlas, project_atlas, render_exr, set_raw_float_output,
    texel_density, uv_material)


LANE_CENTRE = [atlas_allocation.LANE_CENTRE]        # set from --span in main: half the lane


def place_camera(scene, lane_y: float):
    """A lane position in engine space, the mesh being in Blender space (see atlas_allocation)."""
    return atlas_allocation.lane_camera(scene, lane_y, centre=LANE_CENTRE[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cycles-atlas", type=Path, default=None,
                        help="the Cycles atlas for the same room, from study_atlas_drift.py")
    parser.add_argument("--atlas-size", type=int, default=1024)
    parser.add_argument("--layout", choices=("loose", "packed", "view"), default="packed",
                        help="the atlas layout: loose is the original ~23%%-full smart_project layout, "
                             "packed is tight, view also spends the atlas where the lane cameras look")
    parser.add_argument("--probe-volume", type=float, default=0.0, metavar="CELLS_PER_M",
                        help="bake an EEVEE light probe volume over the room before the beauty pass "
                             "(the EEVEE answer to the sealed-room world-fill leak); 0 = off")
    parser.add_argument("--probe-samples", type=int, default=256)
    parser.add_argument("--exposure", type=float, default=0.0, metavar="EV",
                        help="gain, in EV, applied to the EEVEE beauty in linear light before it goes "
                             "into the atlas, and to the EEVEE target frames (matches a plate's exposure)")
    parser.add_argument("--view-bias", type=float, default=0.85)
    parser.add_argument("--view-floor", type=float, default=0.04)
    parser.add_argument("--bake-cameras", type=int, default=9)
    parser.add_argument("--supersample", type=int, default=3)
    parser.add_argument("--span", type=float, default=7.7667)
    parser.add_argument("--ambient", type=float, default=0.13)
    parser.add_argument("--lamp-scale", type=float, default=0.3)
    parser.add_argument("--accent-scale", type=float, default=0.4)
    parser.add_argument("--window-emission-scale", type=float, default=1.0)
    parser.add_argument("--eevee-option", action="append", default=[], metavar="NAME=VALUE",
                        help="scene.eevee overrides for the beauty and target frames, as in stage_room_model.py")
    parser.add_argument("--emissive-lights", action="store_true",
                        help="companion area lights on the emissive patches, as in stage_room_model.py")
    parser.add_argument("--emissive-exclude", action="append", default=[], metavar="MATERIAL")
    parser.add_argument("--fixture-lights", action="store_true",
                        help="let lamps shine out of their fixtures, as in stage_room_model.py")
    parser.add_argument("--cycles-target", action="store_true",
                        help="also render Cycles beauty frames as the engine reference, without an atlas")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    LANE_CENTRE[0] = args.span / 2.0
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    scene = bpy.context.scene
    source = exporter.sort_into_contract_collections()
    allocation_cameras = [0.35 + i * (args.span - 0.7) / 8 for i in range(9)]
    target = exporter.build_render_mesh(source, f"{args.blend.stem}_TH_RENDER", 1.0, layout=args.layout,
                                        atlas_size=args.atlas_size, view_bias=args.view_bias,
                                        view_floor=args.view_floor, cameras=allocation_cameras)
    layout = atlas_allocation.layout_report(target, args.atlas_size)
    stager.base_lighting(args.ambient, (0.0, 0.0, 0.0), stager.INTERIOR_FILL)
    stager.scale_lamp_energy(scene, args.lamp_scale, args.accent_scale)
    stager.scale_window_emission(scene, args.window_emission_scale)
    companions = None
    if args.emissive_lights:
        # From the source meshes, before they are hidden: the joined mesh carries the same emissive
        # materials but the companions are placed on the faces as authored.
        companions = emissive_lights.add_companion_lights(scene, exclude=tuple(args.emissive_exclude), ignore=(target,))
        print("emissive lights: " + json.dumps(companions), flush=True)
    # The joined mesh IS the room: render it, not the source copies it was made from. Only the
    # source MESHES are hidden. `sort_into_contract_collections` puts every object in TH_SOURCE,
    # lamps included, so hiding the collection would leave the room lit by the world fill alone
    # (an earlier draft of this study did exactly that, and looked plausible).
    fixtures = None
    if args.fixture_lights:
        # A lamp inside its own small housing is shadowed by it in EEVEE (see light_fixtures.py), and
        # the joined mesh has the housing welded into the room, so its shadow cannot be switched off
        # for that part alone. So the source meshes stay in the scene as the shadow casters, unseen by
        # the camera, with the housings released, and the joined mesh casts none.
        fixtures = light_fixtures.release_fixture_lights(scene)
        print("fixture lights: " + json.dumps(fixtures), flush=True)
        target.visible_shadow = False
    for obj in source.objects:
        if obj.type == "MESH":
            if args.fixture_lights:
                obj.visible_camera = False
            else:
                obj.hide_render = True
    lamps =[o for o in source.objects if o.type == "LIGHT"]
    if not lamps:
        raise SystemExit("the source .blend has no lights; the study would measure the world fill only")
    scene.render.engine = "BLENDER_EEVEE"
    uv_layer = target.data.uv_layers.active.name
    size = args.atlas_size
    if args.eevee_option:
        print("eevee options: " + json.dumps(stager.apply_eevee_options(scene.eevee, args.eevee_option)), flush=True)
    probe = None
    if args.probe_volume > 0:
        # Baked from the joined mesh alone (the source meshes are hidden above), with the room's lamps.
        probe = stager.add_probe_volume(scene, args.probe_volume, args.probe_samples,
                                        capture_emission=not args.emissive_lights)
        print("probe volume: " + json.dumps(probe), flush=True)

    lo, hi = 0.6, args.span - 0.6
    bake_positions = list(np.linspace(lo, hi, args.bake_cameras))
    step = (hi - lo) / (args.bake_cameras - 1)
    # Held-out cameras: between bake cameras, and the two ends of the walkable lane, which sit
    # OUTSIDE the range the bake sampled (a player can stand there).
    check_positions = [lo + step * 0.5, (lo + hi) / 2 + step * 0.5, hi - step * 0.5, 0.35, args.span - 0.35]

    started = time.time()
    projected = project_atlas(scene, uv_layer, bake_positions, place_camera, size, out,
                              supersample=args.supersample, exposure=args.exposure,
                              log=lambda line: print(line, flush=True))
    eevee_atlas, coverage = finish_atlas(projected, triangle_mask(target.data, size),
                                         "SR_EEVEE_ATLAS", out / "atlas_eevee.png")
    per_camera = projected["cameras"]
    bake_seconds = time.time() - started
    print(f"EEVEE atlas: {json.dumps(coverage)} in {bake_seconds:.1f}s", flush=True)

    # -- judge it from camera positions the bake did not use ---------------------------------
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    crisp(scene)
    atlases = {"eevee": eevee_atlas}
    if args.cycles_atlas:
        cycles_atlas = bpy.data.images.load(str(args.cycles_atlas.resolve()))
        cycles_atlas.colorspace_settings.name = "sRGB"
        atlases["cycles"] = cycles_atlas
    for number, lane_y in enumerate(check_positions):
        place_camera(scene, float(lane_y))
        bpy.context.view_layer.material_override = None
        scene.render.engine = "BLENDER_EEVEE"
        # The exposure gain is a property of the EEVEE lighting: it is on the EEVEE beauty target, and
        # already baked into the EEVEE atlas's texels, so the unlit atlas frames must not apply it twice.
        scene.view_settings.exposure = args.exposure
        scene.render.filepath = str(out / f"target_eevee_{number}.png")
        bpy.ops.render.render(write_still=True)
        scene.view_settings.exposure = 0.0
        if args.cycles_atlas or args.cycles_target:
            scene.render.engine = "CYCLES"
            scene.cycles.samples = 32
            scene.cycles.use_denoising = True
            scene.render.filepath = str(out / f"target_cycles_{number}.png")
            if args.fixture_lights:
                # The Cycles reference is the room as it is today: one joined mesh that casts shadows,
                # its source copies out of the scene. (Left as the EEVEE lighting set-up it is twice as bright.)
                target.visible_shadow = True
                for obj in source.objects:
                    if obj.type == "MESH":
                        obj.hide_render = True
            bpy.ops.render.render(write_still=True)
            if args.fixture_lights:
                target.visible_shadow = False
                for obj in source.objects:
                    if obj.type == "MESH":
                        obj.hide_render = False
            scene.render.engine = "BLENDER_EEVEE"
        for name, image in atlases.items():
            bpy.context.view_layer.material_override = atlas_material(image)
            scene.render.filepath = str(out / f"atlas_{name}_{number}.png")
            bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.material_override = None
    # -- how many texels the atlas spends per screen pixel, at the check cameras ---------------
    scene.render.engine = "BLENDER_EEVEE"
    uv_mat = uv_material(uv_layer)
    densities = []
    for lane_y in check_positions:
        place_camera(scene, float(lane_y))
        bpy.context.view_layer.material_override = uv_mat
        scene.eevee.taa_render_samples = 1
        scene.render.filter_size = 0.0
        set_raw_float_output(scene, out / "tmp_uv.exr", 1)
        densities.append(texel_density(render_exr(scene, out / "tmp_uv.exr"), size))
        bpy.context.view_layer.material_override = None
    (out / "tmp_uv.exr").unlink(missing_ok=True)
    density = np.concatenate(densities)
    density_report = {"pixelsMeasured": int(density.size),
                      "p10": round(float(np.percentile(density, 10)), 3),
                      "median": round(float(np.median(density)), 3),
                      "p90": round(float(np.percentile(density, 90)), 3),
                      "fractionBelowHalf": round(float((density < 0.5).mean()), 4),
                      "fractionBelowOne": round(float((density < 1.0).mean()), 4)}
    print("texels per screen pixel: " + json.dumps(density_report), flush=True)
    (out / "result.json").write_text(json.dumps({
        "blend": args.blend.name, "atlasSize": size, "bakeCameras": per_camera,
        "checkCameras": [round(float(y), 3) for y in check_positions],
        "layout": args.layout, "layoutCoverage": layout, "probeVolume": probe, "emissiveLights": companions, "fixtureLights": fixtures, "lampScale": args.lamp_scale, "exposureEV": args.exposure, "texelsPerPixel": density_report,
        "coverage": coverage, "eeveeBakeSeconds": round(bake_seconds, 1),
        "supersample": args.supersample}, indent=1), encoding="utf-8")
    print("EEVEE ATLAS STUDY OK", out)


if __name__ == "__main__":
    main()
