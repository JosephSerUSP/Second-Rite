"""Bake an atlas with EEVEE, by camera projection: the shared core of the EEVEE atlas bake.

EEVEE has no bake (`bpy.ops.object.bake` refuses), so an atlas is made by photographing the mesh. For
each lane camera: a beauty frame (what EEVEE renders, raw linear float) and a UV frame of the same
view (an emission override painting each pixel with its own (u, v)). Every beauty pixel is splatted
into the atlas texel its UV names, and a texel is the mean, in linear light, of everything that
landed on it. Texels no camera saw stay empty; `dilate` grows the seen ones a few texels.

What a caller decides, and this module does not: the lighting, the cameras, which objects the beauty
frame sees (`beauty_pass`) and which the UV frame sees (`uv_pass`). An interior renders its joined
mesh for both. An exterior's joined mesh has no real materials (the ground carries an allocation
tag), so its beauty frame is of the source meshes and its UV frame of the joined one.

Every frame that stands for what a player sees is rendered with no reconstruction filter: the game
rasterises at native pixels and samples the atlas nearest, and EEVEE's default 1.5 px filter blurs
a frame by about a pixel (docs/reports/eevee-atlas-and-grass-placement-2026-09-30.md, correction 1b).

Blender-side: import it from a script run with `blender --python`.
"""
from __future__ import annotations

from pathlib import Path

import bpy
import numpy as np
import render_profiles

VIEW_WIDTH = 426          # the wide view; 256 is the classic one inside it
VIEW_HEIGHT = 240
DILATION = 4                 # the Cycles bake also dilates by 4


def crisp(scene):
    render_profiles.apply(scene, render_profiles.resolve("export", engine="eevee"))


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


def uv_material(uv_layer: str, opacity=None):
    material = bpy.data.materials.new("SR_UV_PASS")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_layer
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(uv.outputs["UV"], emission.inputs["Color"])
    if opacity is None:
        tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    else:
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image = opacity
        texture.interpolation = "Closest"
        tree.links.new(uv.outputs["UV"], texture.inputs["Vector"])
        transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
        mix = tree.nodes.new("ShaderNodeMixShader")
        cutout = tree.nodes.new("ShaderNodeMath")
        cutout.operation = "GREATER_THAN"
        cutout.inputs[1].default_value = 0.01  # runtime discard threshold; UVs must never blend between surfaces
        tree.links.new(texture.outputs["Color"], cutout.inputs[0])
        tree.links.new(cutout.outputs[0], mix.inputs[0])
        tree.links.new(transparent.outputs[0], mix.inputs[1])
        tree.links.new(emission.outputs[0], mix.inputs[2])
        tree.links.new(mix.outputs[0], output.inputs["Surface"])
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
    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    mix = tree.nodes.new("ShaderNodeMixShader")
    tree.links.new(texture.outputs["Alpha"], mix.inputs[0])
    tree.links.new(transparent.outputs[0], mix.inputs[1])
    tree.links.new(emission.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], output.inputs["Surface"])
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


def project_atlas(scene, uv_layer: str, positions, place_camera, size: int, out: Path,
                  supersample: int = 3, exposure: float = 0.0, beauty_pass=None, uv_pass=None,
                  log=print, opacity=None) -> dict:
    """Photograph the scene from every lane position and splat it into an atlas.

    `place_camera(scene, lane_y)` puts the lane camera where the player would stand.
    `beauty_pass()` / `uv_pass()` (optional) set up what each frame sees, before the frame is rendered.
    Returns {"linear": (size, size, 3) mean linear colour, "seen": (size, size) bool, "cameras": [...]}.
    """
    uv_mat = uv_material(uv_layer, opacity)
    total = np.zeros(size * size * 3, dtype=np.float64)
    weight = np.zeros(size * size, dtype=np.float64)
    cameras = []
    for number, lane_y in enumerate(positions):
        place_camera(scene, float(lane_y))
        # Beauty: the scene as EEVEE lights it.
        if beauty_pass is not None:
            beauty_pass()
        bpy.context.view_layer.material_override = None
        crisp(scene)
        set_raw_float_output(scene, out / "tmp_beauty.exr", supersample)
        beauty = render_exr(scene, out / "tmp_beauty.exr")
        # UV: every pixel names its own texel. No antialiasing, no filter, no view transform.
        if uv_pass is not None:
            uv_pass()
        bpy.context.view_layer.material_override = uv_mat
        scene.eevee.taa_render_samples = 1
        scene.render.filter_size = 0.0
        set_raw_float_output(scene, out / "tmp_uv.exr", supersample)
        uv = render_exr(scene, out / "tmp_uv.exr")
        bpy.context.view_layer.material_override = None
        hit = uv[..., 3] > 0.5
        ix = np.clip((uv[..., 0][hit] * size).astype(np.int64), 0, size - 1)
        iy = np.clip((uv[..., 1][hit] * size).astype(np.int64), 0, size - 1)
        flat = iy * size + ix
        colours = np.clip(beauty[..., :3][hit].astype(np.float64), 0.0, None) * (2.0 ** exposure)
        for channel in range(3):
            total[channel::3] += np.bincount(flat, weights=colours[:, channel], minlength=size * size)
        weight += np.bincount(flat, minlength=size * size)
        cameras.append({"laneY": round(float(lane_y), 3), "pixels": int(hit.sum())})
        log(f"  bake camera {number + 1}/{len(positions)} lane y {lane_y:.2f}: {int(hit.sum())} pixels")
    for name in ("tmp_beauty.exr", "tmp_uv.exr"):
        (out / name).unlink(missing_ok=True)
    seen = weight > 0
    linear = np.zeros((size * size, 3))
    linear[seen] = total.reshape(-1, 3)[seen] / weight[seen][:, None]
    return {"linear": linear.reshape(size, size, 3), "seen": seen.reshape(size, size), "cameras": cameras}


def finish_atlas(projected: dict, islands: np.ndarray, name: str, path: Path | None,
                 image=None) -> tuple[object, dict]:
    """Dilate and encode to sRGB. Returns (the Blender image, what the atlas covers).

    With `image` the texels go into that image (the exporter's bake target, which it saves itself);
    otherwise a new image is made and saved to `path`.
    """
    size = projected["linear"].shape[0]
    seen = projected["seen"]
    filled, reached = dilate(projected["linear"], seen, DILATION)
    coverage = {"islandTexels": int(islands.sum()), "seenTexels": int((seen & islands).sum()),
                "seenFractionOfIslands": round(float((seen & islands).sum() / max(1, islands.sum())), 4),
                "afterDilationFraction": round(float((reached & islands).sum() / max(1, islands.sum())), 4)}
    atlas = np.zeros((size, size, 4), dtype=np.float32)
    atlas[..., :3] = srgb_encode(filled)
    atlas[..., 3] = 1.0
    if image is None:
        image = bpy.data.images.new(name, size, size, alpha=True)
        image.pixels.foreach_set(atlas.reshape(-1))
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
    else:
        image.pixels.foreach_set(atlas.reshape(-1))
    return image, coverage
