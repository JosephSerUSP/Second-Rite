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
import export_room_environment as exporter  # noqa: E402
import stage_room_model as stager  # noqa: E402
import atlas_allocation  # noqa: E402
from atlas_allocation import triangle_mask  # noqa: E402
import thestra_camera  # noqa: E402

CAMERA_RECORD = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"
VIEW_WIDTH = 426          # the wide view; 256 is the classic one inside it

# Every render here that stands for what a player sees uses NO reconstruction filter. The game
# rasterises at native pixels and samples the atlas nearest, so Film > Filter Size (EEVEE's default
# is 1.5 px, Cycles' filter width the same) blurs a frame by about a pixel and makes the atlas look
# far softer than it is: measured on a Padaria frame, Laplacian variance 511 at 1.5 against 2,755 at
# 0. The lighting samples still accumulate (64), so the frame is converged, just not blurred.
FILM_FILTER = 0.0
TAA_SAMPLES = 64
CYCLES_FILTER_WIDTH = 0.01   # Cycles' minimum; it will not take 0


def crisp(scene):
    scene.eevee.taa_render_samples = TAA_SAMPLES
    scene.render.filter_size = FILM_FILTER
    scene.cycles.filter_width = CYCLES_FILTER_WIDTH
VIEW_HEIGHT = 240


def srgb_encode(linear: np.ndarray) -> np.ndarray:
    c = np.clip(linear, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def srgb_decode(encoded: np.ndarray) -> np.ndarray:
    return np.where(encoded <= 0.04045, encoded / 12.92, np.power((encoded + 0.055) / 1.055, 2.4))


def set_raw_float_output(scene, path: Path, supersample: int):
    scene.render.resolution_x = VIEW_WIDTH
    scene.render.resolution_y = VIEW_HEIGHT
    scene.render.resolution_percentage = 100 * supersample
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Raw"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.filepath = str(path)


def render_exr(scene, path: Path) -> np.ndarray:
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path))
    try:
        width, height = image.size
        buffer = np.empty(width * height * 4, dtype=np.float32)
        image.pixels.foreach_get(buffer)
        return buffer.reshape(height, width, 4)          # row 0 is the bottom, as Blender stores it
    finally:
        bpy.data.images.remove(image)


def uv_material(uv_layer: str):
    material = bpy.data.materials.new("SR_UV_PASS")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_layer
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(uv.outputs["UV"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def atlas_material(image):
    material = bpy.data.materials.new("SR_ATLAS_UNLIT")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Closest"            # the runtime samples nearest, with no mipmaps
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(texture.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def texel_density(uv: np.ndarray, size: int) -> np.ndarray:
    """Texels per screen pixel (linear) at every pixel whose neighbourhood is one smooth surface.

    From the UV frame: how far (u, v) moves, in texels, for one pixel step. The square root of
    the footprint's area is the linear density; 1.0 means one texel per pixel, below 1 the
    atlas is coarser than the screen there.
    """
    hit = uv[..., 3] > 0.5
    u = uv[..., 0] * size
    v = uv[..., 1] * size
    du_dy, du_dx = np.gradient(u)
    dv_dy, dv_dx = np.gradient(v)
    area = np.abs(du_dx * dv_dy - du_dy * dv_dx)
    inner = hit.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            inner &= np.roll(np.roll(hit, dy, axis=0), dx, axis=1)
    smooth = inner & (np.abs(du_dx) < 8) & (np.abs(du_dy) < 8) & (np.abs(dv_dx) < 8) & (np.abs(dv_dy) < 8)
    return np.sqrt(area[smooth])


def dilate(rgb: np.ndarray, filled: np.ndarray, steps: int):
    rgb, filled = rgb.copy(), filled.copy()
    for _ in range(steps):
        total = np.zeros_like(rgb)
        count = np.zeros(filled.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            shifted = np.roll(np.roll(filled, dy, axis=0), dx, axis=1)
            total += np.roll(np.roll(rgb * filled[..., None], dy, axis=0), dx, axis=1)
            count += shifted
        grow = (~filled) & (count > 0)
        rgb[grow] = total[grow] / count[grow][:, None]
        filled |= grow
    return rgb, filled


def place_camera(scene, lane_y: float):
    """A lane position in engine space, the mesh being in Blender space (see atlas_allocation)."""
    return atlas_allocation.lane_camera(scene, lane_y)


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
    parser.add_argument("--view-bias", type=float, default=0.85)
    parser.add_argument("--view-floor", type=float, default=0.04)
    parser.add_argument("--bake-cameras", type=int, default=9)
    parser.add_argument("--supersample", type=int, default=3)
    parser.add_argument("--span", type=float, default=7.7667)
    parser.add_argument("--ambient", type=float, default=0.13)
    parser.add_argument("--lamp-scale", type=float, default=0.3)
    parser.add_argument("--accent-scale", type=float, default=0.4)
    parser.add_argument("--window-emission-scale", type=float, default=1.0)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
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
    # The joined mesh IS the room: render it, not the source copies it was made from. Only the
    # source MESHES are hidden. `sort_into_contract_collections` puts every object in TH_SOURCE,
    # lamps included, so hiding the collection would leave the room lit by the world fill alone
    # (an earlier draft of this study did exactly that, and looked plausible).
    for obj in source.objects:
        if obj.type == "MESH":
            obj.hide_render = True
    lamps = [o for o in source.objects if o.type == "LIGHT"]
    if not lamps:
        raise SystemExit("the source .blend has no lights; the study would measure the world fill only")
    scene.render.engine = "BLENDER_EEVEE"
    uv_layer = target.data.uv_layers.active.name
    size = args.atlas_size

    lo, hi = 0.6, args.span - 0.6
    bake_positions = list(np.linspace(lo, hi, args.bake_cameras))
    step = (hi - lo) / (args.bake_cameras - 1)
    # Held-out cameras: between bake cameras, and the two ends of the walkable lane, which sit
    # OUTSIDE the range the bake sampled (a player can stand there).
    check_positions = [lo + step * 0.5, (lo + hi) / 2 + step * 0.5, hi - step * 0.5, 0.35, args.span - 0.35]

    started = time.time()
    total = np.zeros(size * size * 3, dtype=np.float64)
    weight = np.zeros(size * size, dtype=np.float64)
    uv_mat = uv_material(uv_layer)
    per_camera = []
    for number, lane_y in enumerate(bake_positions):
        place_camera(scene, float(lane_y))
        # Beauty: the room as EEVEE lights it.
        bpy.context.view_layer.material_override = None
        crisp(scene)
        set_raw_float_output(scene, out / "tmp_beauty.exr", args.supersample)
        beauty = render_exr(scene, out / "tmp_beauty.exr")
        # UV: every pixel names its own texel. No antialiasing, no filter, no view transform.
        bpy.context.view_layer.material_override = uv_mat
        scene.eevee.taa_render_samples = 1
        scene.render.filter_size = 0.0
        set_raw_float_output(scene, out / "tmp_uv.exr", args.supersample)
        uv = render_exr(scene, out / "tmp_uv.exr")
        bpy.context.view_layer.material_override = None
        hit = uv[..., 3] > 0.5
        ix = np.clip((uv[..., 0][hit] * size).astype(np.int64), 0, size - 1)
        iy = np.clip((uv[..., 1][hit] * size).astype(np.int64), 0, size - 1)
        flat = iy * size + ix
        colours = np.clip(beauty[..., :3][hit].astype(np.float64), 0.0, None)
        for channel in range(3):
            total[channel::3] += np.bincount(flat, weights=colours[:, channel], minlength=size * size)
        weight += np.bincount(flat, minlength=size * size)
        per_camera.append({"laneY": round(float(lane_y), 3), "pixels": int(hit.sum())})
        print(f"  bake camera {number + 1}/{args.bake_cameras} lane y {lane_y:.2f}: {int(hit.sum())} pixels", flush=True)
    for name in ("tmp_beauty.exr", "tmp_uv.exr"):
        (out / name).unlink(missing_ok=True)

    seen = weight > 0
    linear = np.zeros((size * size, 3))
    linear[seen] = total.reshape(-1, 3)[seen] / weight[seen][:, None]
    linear = linear.reshape(size, size, 3)
    seen = seen.reshape(size, size)
    islands = triangle_mask(target.data, size)
    filled, reached = dilate(linear, seen, 4)               # the Cycles bake also dilates by 4
    coverage = {"islandTexels": int(islands.sum()), "seenTexels": int((seen & islands).sum()),
                "seenFractionOfIslands": round(float((seen & islands).sum() / max(1, islands.sum())), 4),
                "afterDilationFraction": round(float((reached & islands).sum() / max(1, islands.sum())), 4)}
    atlas = np.zeros((size, size, 4), dtype=np.float32)
    atlas[..., :3] = srgb_encode(filled)
    atlas[..., 3] = 1.0
    eevee_atlas = bpy.data.images.new("SR_EEVEE_ATLAS", size, size, alpha=True)
    eevee_atlas.pixels.foreach_set(atlas.reshape(-1))
    eevee_atlas.filepath_raw = str(out / "atlas_eevee.png")
    eevee_atlas.file_format = "PNG"
    eevee_atlas.save()
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
        scene.render.filepath = str(out / f"target_eevee_{number}.png")
        bpy.ops.render.render(write_still=True)
        if args.cycles_atlas:
            scene.render.engine = "CYCLES"
            scene.cycles.samples = 32
            scene.cycles.use_denoising = True
            scene.render.filepath = str(out / f"target_cycles_{number}.png")
            bpy.ops.render.render(write_still=True)
            scene.render.engine = "BLENDER_EEVEE"
        for name, image in atlases.items():
            bpy.context.view_layer.material_override = atlas_material(image)
            scene.render.filepath = str(out / f"atlas_{name}_{number}.png")
            bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.material_override = None
    # -- how many texels the atlas spends per screen pixel, at the check cameras ---------------
    scene.render.engine = "BLENDER_EEVEE"
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
        "layout": args.layout, "layoutCoverage": layout, "texelsPerPixel": density_report,
        "coverage": coverage, "eeveeBakeSeconds": round(bake_seconds, 1),
        "supersample": args.supersample}, indent=1), encoding="utf-8")
    print("EEVEE ATLAS STUDY OK", out)


if __name__ == "__main__":
    main()
