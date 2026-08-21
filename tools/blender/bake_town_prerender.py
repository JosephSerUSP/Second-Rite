"""Bake the edited Second Gate town blend into a layered 2D runtime scene.

The authoring camera remains the visual authority.  The bake keeps two color
layers: geometry behind the authored player plane and geometry in front of it.
Runtime actors are drawn between those layers, so the foreground railings and
statue occlude sprites without requiring the dense source mesh at play time.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path


def _after_double_dash(argv):
    return argv[argv.index("--") + 1:] if "--" in argv else []


def _configure_depth_compositor(scene, depth_dir: Path):
    import bpy

    scene.use_nodes = True
    tree = scene.compositing_node_group
    if tree is None:
        tree = bpy.data.node_groups.new("TownPrerenderCompositor", "CompositorNodeTree")
        scene.compositing_node_group = tree
    tree.nodes.clear()
    layers = tree.nodes.new("CompositorNodeRLayers")
    layers.layer = scene.view_layers[0].name
    output_node = tree.nodes.new("CompositorNodeOutputFile")
    output_node.file_output_items.new("FLOAT", "Depth")
    output_node.format.file_format = "OPEN_EXR_MULTILAYER"
    output_node.format.color_mode = "RGBA"
    output_node.directory = str(depth_dir) + os.sep
    output_node.file_name = "depth"
    tree.links.new(layers.outputs["Depth"], output_node.inputs["Depth"])


def _clear_depth_files(path: Path) -> None:
    for candidate in path.glob("depth*.exr"):
        candidate.unlink()


def _latest_depth(depth_dir: Path) -> Path:
    candidates = sorted(depth_dir.glob("depth*.exr"), key=lambda item: item.stat().st_mtime)
    if not candidates:
        raise RuntimeError("Blender did not produce a depth pass")
    return candidates[-1]


def _read_depth(path: Path):
    import OpenImageIO as oiio

    image = oiio.ImageInput.open(str(path))
    if not image:
        raise RuntimeError(f"cannot read Blender depth pass: {path}")
    spec = image.spec()
    values = image.read_image(oiio.FLOAT)
    image.close()
    # OpenImageIO exposes EXR rows from the top of the image while Blender's
    # Image.pixels sequence (used by _save_layer) is bottom-up. Normalize the
    # depth pass to Blender's order here so an alpha mask lands on the same
    # rendered pixel instead of being vertically mirrored.
    return spec.width, spec.height, [float(values[spec.height - 1 - row, column, 0])
                                     for row in range(spec.height)
                                     for column in range(spec.width)]


def _save_layer(bpy, name: str, output: Path, beauty, depth, threshold, front: bool,
                width: int, height: int) -> None:
    pixels = list(beauty)
    visible_count = 0
    for index in range(width * height):
        source_depth = depth[index]
        threshold_depth = threshold[index]
        finite = math.isfinite(source_depth) and source_depth > 0.0
        visible = finite and ((source_depth < threshold_depth)
                              if front else (source_depth >= threshold_depth))
        if visible:
            visible_count += 1
        pixels[index * 4 + 3] = 1.0 if visible else 0.0

    image = bpy.data.images.new(name, width=width, height=height, alpha=True)
    image.pixels = pixels
    image.filepath_raw = str(output)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    print(f"[prerender] {output.name}: {visible_count}/{width * height} pixels")


def _save_scene(bpy, name: str, output: Path, beauty, width: int, height: int) -> None:
    """Save the complete opaque camera slice used for the scene underlay."""
    image = bpy.data.images.new(name, width=width, height=height, alpha=True)
    image.pixels = list(beauty)
    image.filepath_raw = str(output)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def _project(bpy, scene, camera, point, width: int, height: int):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector

    ndc = world_to_camera_view(scene, camera, Vector(point))
    return ndc.x * width, (1.0 - ndc.y) * height


def _write_placeholder_geometry(output: Path, texture_name: str) -> None:
    (output / "environment.obj").write_text(
        "# Layered prerender package placeholder; runtime does not load this mesh.\n"
        "mtllib environment.mtl\n"
        "o PreRenderedEnvironmentPlaceholder\n"
        "v 7.8 5.5 -1.5\n"
        "v 7.801 5.5 -1.5\n"
        "v 7.8 5.501 -1.5\n"
        "usemtl PreRenderedEnvironment\n"
        "f 1 2 3\n",
        encoding="utf-8",
    )
    (output / "environment.mtl").write_text(
        "# Layered prerender package placeholder material\n"
        "newmtl PreRenderedEnvironment\n"
        "Ka 1.000 1.000 1.000\n"
        "Kd 1.000 1.000 1.000\n"
        f"map_Kd {texture_name}\n",
        encoding="utf-8",
    )


def _write_collision(output: Path, anchors: dict) -> None:
    spawn = anchors.get("spawn_player", {}).get("position", [7.8, 5.5, -1.5])
    # The bounded lane remains gameplay authority.  This small envelope keeps
    # the package contract complete for future collision consumers.
    x, y, z = spawn
    corners_world = [
        (x - 0.5, -2.0, z),
        (x + 0.5, -2.0, z),
        (x + 0.5, 13.0, z),
        (x - 0.5, 13.0, z),
    ]
    # Environment OBJ files use (world X, world Z, -world Y).  Keep the
    # collision envelope in that same coordinate convention as the regular
    # Meshy package builder.
    corners_obj = [(world_x, world_z, -world_y)
                   for world_x, world_y, world_z in corners_world]
    (output / "collision.obj").write_text(
        "# Bounded-lane collision envelope for layered prerender\n"
        + "".join(f"v {world_x:.6f} {world_z:.6f} {world_y:.6f}\n"
                  for world_x, world_z, world_y in corners_obj)
        + "f 1 2 3\n"
        + "f 1 3 4\n",
        encoding="utf-8",
    )


def run_in_blender(blend_path: Path, output: Path, anchors_path: Path,
                   runtime_min: float, runtime_max: float,
                   runtime_center: float, runtime_scale: float,
                   slice_step: float) -> None:
    import bpy
    from mathutils import Vector

    output.mkdir(parents=True, exist_ok=True)
    depth_dir = output / ".depth"
    depth_dir.mkdir(parents=True, exist_ok=True)
    beauty_dir = output / ".beauty"
    beauty_dir.mkdir(parents=True, exist_ok=True)
    for old_name in ("background.png", "foreground.png", "beauty_full.png"):
        old_path = output / old_name
        if old_path.exists():
            old_path.unlink()
    shutil.rmtree(output / ".mask", ignore_errors=True)
    for old in output.glob("background_*.png"):
        old.unlink()
    for old in output.glob("foreground_*.png"):
        old.unlink()
    for old in output.glob("scene_*.png"):
        old.unlink()

    scene = bpy.context.scene
    camera = bpy.data.objects.get("CAMERA_PLAYER_VIEW")
    source = bpy.data.objects.get("Meshy_Village_Source")
    spawn = bpy.data.objects.get("SPAWN_PLAYER")
    walkable = bpy.data.objects.get("WALKABLE_MAIN")
    walker = bpy.data.objects.get("WALKER_SPRITE")
    if not camera or not source or not spawn or not walkable or not walker:
        raise RuntimeError("blend must contain CAMERA_PLAYER_VIEW, Meshy_Village_Source, "
                           "SPAWN_PLAYER, WALKABLE_MAIN and WALKER_SPRITE")

    scene.camera = camera
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_layers[0].use_pass_z = True

    # The source mesh is the only renderable geometry.  Annotation meshes and
    # the preview actor remain available in the .blend but never enter the bake.
    for obj in bpy.data.objects:
        if obj == source or obj.type == "LIGHT" or obj.type == "CAMERA":
            obj.hide_render = False
        else:
            obj.hide_render = True

    width = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
    height = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)
    print(f"[prerender] rendering camera-centered slices at {width}x{height}")

    # The player moves across authoring X while the saved camera looks along
    # authoring +Y.  A plane at the player depth gives an exact per-pixel depth
    # threshold, including perspective and camera pitch.
    player_position = spawn.matrix_world.translation
    plane_mesh = bpy.data.meshes.new("__TownPlayerDepthPlaneMesh")
    plane_mesh.from_pydata([
        (-100.0, 0.0, -100.0), (100.0, 0.0, -100.0),
        (100.0, 0.0, 100.0), (-100.0, 0.0, 100.0),
    ], [], [(0, 1, 2, 3)])
    plane = bpy.data.objects.new("__TownPlayerDepthPlane", plane_mesh)
    scene.collection.objects.link(plane)
    plane.location = (0.0, player_position.y, 0.0)
    plane.hide_render = True
    source.hide_render = True
    original_shift_x = camera.data.shift_x
    slice_positions = []
    background_files = []
    foreground_files = []
    scene_files = []
    cursor = runtime_min
    while cursor < runtime_max - 1e-6:
        slice_positions.append(round(cursor, 5))
        cursor += slice_step
    slice_positions.append(round(runtime_max, 5))

    for slice_index, runtime_y in enumerate(slice_positions):
        author_x = float(player_position.x) + (runtime_y - runtime_center) / runtime_scale
        # world_to_camera_view includes the camera's current shift. Reset it
        # before measuring each slice, otherwise the correction accumulates
        # from one slice to the next.
        camera.data.shift_x = original_shift_x
        base_screen_x, _ = _project(
            bpy, scene, camera, (author_x, player_position.y, player_position.z), width, height)
        # Blender's camera shift moves the rendered image in the same screen
        # direction as this correction. Negating the NDC offset keeps the
        # authored player position at the center of every slice and makes
        # fixed landmarks move opposite to the player's lane motion.
        camera.data.shift_x = base_screen_x / width - 0.5

        # Beauty layer.
        source.hide_render = False
        plane.hide_render = True
        scene.use_nodes = False
        beauty_path = beauty_dir / f"beauty_{slice_index:03d}.png"
        scene.render.filepath = str(beauty_path)
        bpy.ops.render.render(write_still=True)
        beauty_image = bpy.data.images.load(str(beauty_path), check_existing=False)
        beauty = list(beauty_image.pixels[:])
        bpy.data.images.remove(beauty_image)

        # Source depth layer.
        scene.render.film_transparent = False
        _configure_depth_compositor(scene, depth_dir)
        _clear_depth_files(depth_dir)
        bpy.ops.render.render()
        depth_width, depth_height, base_depth = _read_depth(_latest_depth(depth_dir))
        if (depth_width, depth_height) != (width, height):
            raise RuntimeError("source depth pass dimensions differ from beauty render")

        # Player-plane depth layer.
        source.hide_render = True
        plane.hide_render = False
        _clear_depth_files(depth_dir)
        bpy.ops.render.render()
        depth_width, depth_height, player_depth = _read_depth(_latest_depth(depth_dir))
        if (depth_width, depth_height) != (width, height):
            raise RuntimeError("player depth pass dimensions differ from beauty render")

        source.hide_render = False
        plane.hide_render = True
        background_name = f"background_{slice_index:03d}.png"
        foreground_name = f"foreground_{slice_index:03d}.png"
        scene_name = f"scene_{slice_index:03d}.png"
        _save_scene(bpy, "TownScene", output / scene_name, beauty, width, height)
        _save_layer(bpy, "TownBackground", output / background_name, beauty,
                    base_depth, player_depth, False, width, height)
        _save_layer(bpy, "TownForeground", output / foreground_name, beauty,
                    base_depth, player_depth, True, width, height)
        background_files.append(background_name)
        foreground_files.append(foreground_name)
        scene_files.append(scene_name)
        print(f"[prerender] slice {slice_index + 1}/{len(slice_positions)} runtimeY={runtime_y}")

    camera.data.shift_x = original_shift_x
    source.hide_render = False
    plane.hide_render = True
    bpy.data.objects.remove(plane, do_unlink=True)
    bpy.data.meshes.remove(plane_mesh)
    shutil.rmtree(depth_dir, ignore_errors=True)
    shutil.rmtree(beauty_dir, ignore_errors=True)

    spawn_x = float(player_position.x)
    spawn_y = float(player_position.y)
    spawn_z = float(player_position.z)
    walker_width = max(float(walker.dimensions.x), 1e-6)
    walker_height = max(float(walker.dimensions.z), 1e-6)
    camera.data.shift_x = original_shift_x
    center_foot = _project(bpy, scene, camera, (spawn_x, spawn_y, spawn_z), width, height)
    next_foot = _project(
        bpy, scene, camera,
        (spawn_x + 1.0 / runtime_scale, spawn_y, spawn_z), width, height)
    left = _project(bpy, scene, camera,
                    (spawn_x - walker_width * 0.5, spawn_y, spawn_z), width, height)
    right = _project(bpy, scene, camera,
                     (spawn_x + walker_width * 0.5, spawn_y, spawn_z), width, height)
    top = _project(bpy, scene, camera,
                   (spawn_x, spawn_y, spawn_z + walker_height), width, height)
    pixels_per_runtime_y = next_foot[0] - center_foot[0]
    samples = []
    for runtime_y in slice_positions:
        samples.append({
            "runtimeY": round(runtime_y, 5),
            "screenX": round(width * 0.5, 4),
            "screenY": round(center_foot[1], 4),
            "width": round(abs(right[0] - left[0]), 4),
            "height": round(abs(center_foot[1] - top[1]), 4),
        })

    anchors = {}
    if anchors_path.is_file():
        anchors = json.loads(anchors_path.read_text(encoding="utf-8")).get("anchors", {})
    anchors.setdefault("spawn_player", {
        "id": "spawn_player", "position": [7.8, 5.5, -1.5],
        "rotation": [0.0, 0.0, 0.0], "forward": [0.0, 1.0, 0.0],
    })
    _write_placeholder_geometry(output, background_files[0])
    _write_collision(output, anchors)
    manifest = {
        "contractVersion": 1,
        "environmentId": "town_church_prerender",
        "renderMesh": "environment.obj",
        "materialLibrary": "environment.mtl",
        "textureAtlas": background_files[0],
        "collisionMesh": "collision.obj",
        "bounds": [5.75, -2.0, -1.6, 12.8, 13.0, 4.5],
        "stats": {
            "triangleCount": 1,
            "vertexCount": 3,
            "materialGroupCount": 1,
            "textureDimensions": [width, height],
            "pngSizeBytes": sum((output / name).stat().st_size
                                 for name in background_files + foreground_files + scene_files),
            "renderMeshSizeBytes": (output / "environment.obj").stat().st_size,
            "packageSizeBytes": sum(path.stat().st_size for path in output.iterdir()
                                     if path.is_file()),
        },
        "anchors": anchors,
        "preRendered": {
            "mode": "layered_2d",
            "background": background_files[0],
            "foreground": foreground_files[0],
            "backgrounds": background_files,
            "foregrounds": foreground_files,
            "scenes": scene_files,
            "slicePositions": slice_positions,
            "sliceStep": round(slice_step, 5),
            "imageSize": [width, height],
            "lane": {
                "runtimeMinY": runtime_min,
                "runtimeMaxY": runtime_max,
                "runtimeCenterY": runtime_center,
                "runtimeToAuthorScale": runtime_scale,
                "authoringLaneAxis": "x",
                "authoringPlayerDepth": round(spawn_y, 6),
            },
            "playerProjection": {
                "samples": samples,
                "centerX": round(width * 0.5, 4),
                "screenY": round(center_foot[1], 4),
                "width": round(abs(right[0] - left[0]), 4),
                "height": round(abs(center_foot[1] - top[1]), 4),
                "pixelsPerRuntimeY": round(pixels_per_runtime_y, 6),
                "worldWidth": round(walker_width, 6),
                "worldHeight": round(walker_height, 6),
            },
        },
        "provenance": {
            "generator": "tools/blender/bake_town_prerender.py",
            "sourceBlend": blend_path.name,
            "sourceCamera": camera.name,
            "sourceResolution": [width, height],
            "walkableObject": walkable.name,
        },
    }
    (output / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "imageSize": [width, height],
        "projectionSamples": len(samples),
        "sliceCount": len(slice_positions),
        "backgroundBytes": sum((output / name).stat().st_size for name in background_files),
        "foregroundBytes": sum((output / name).stat().st_size for name in foreground_files),
    }, indent=2))


def main() -> None:
    args = _after_double_dash(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("blend", type=Path, nargs="?")
    parser.add_argument("--output", "-o", required=True, type=Path)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--runtime-min", type=float, default=-2.0)
    parser.add_argument("--runtime-max", type=float, default=13.0)
    parser.add_argument("--runtime-center", type=float, default=5.5)
    parser.add_argument("--runtime-scale", type=float, default=8.0)
    parser.add_argument("--slice-step", type=float, default=0.375)
    options = parser.parse_args(args)
    blend_path = options.blend
    if blend_path is None:
        import bpy
        blend_path = Path(bpy.data.filepath)
    run_in_blender(blend_path.resolve(), options.output.resolve(),
                   options.anchors.resolve(), options.runtime_min,
                   options.runtime_max, options.runtime_center,
                   options.runtime_scale, options.slice_step)


if __name__ == "__main__":
    main()
