"""Stage a generated room model against the calibrated Second Gate town camera.

This is the Blender step of the plate -> Tripo -> Blender -> engine workflow.
Its job is NOT to author a camera: the camera is derived from the engine's
resolved WorldCamera through `thestra_camera`, and the actor's on-screen pixel
scale is a fixed consequence of that record. What the artist adjusts here is
the MODEL (how many world units tall the room really is) and the LIGHTING.

Because the lens is fixed and camera distance is solved, establishing the
room's world scale is the whole game: say how tall the interior is in world
units and the character-to-screen ratio follows automatically.

Run:

    blender --background --python tools/blender/stage_room_model.py -- \
        --model out/hall.glb --model-height 7.0 \
        --out out/hall.blend --render out/hall.png

The script asserts the Walker still projects to the expected native pixel
height and fails loudly if it does not.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import material_library  # noqa: E402
import second_rite_asset_core as asset_core  # noqa: E402
import thestra_camera  # noqa: E402

DEFAULT_CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"
DEFAULT_WALKER = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
WALKER_WORLD_HEIGHT = 1.75
WALKER_NATIVE_PIXELS = 48.0
MODEL_COLLECTION = "TH_SOURCE"


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def imported_meshes(before: set) -> list:
    return [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]


def world_bounds(objects) -> tuple[Vector, Vector]:
    """Measure through the evaluated depsgraph.

    `object.bound_box` and `object.matrix_world` are not reliably in sync in
    background mode right after an import or a scale assignment; reading them
    directly can silently return local-space numbers and produce a wrong
    normalisation factor.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    found = False
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh is None:
            continue
        matrix = evaluated.matrix_world
        for vertex in mesh.vertices:
            point = matrix @ vertex.co
            found = True
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
        evaluated.to_mesh_clear()
    if not found:
        raise SystemExit("imported model has no mesh geometry to measure")
    return Vector(lo), Vector(hi)


def upward_faces(objects):
    """World-space (area, z) for every upward-facing polygon."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    out = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh is None:
            continue
        matrix = evaluated.matrix_world
        normal_matrix = matrix.to_3x3().inverted_safe().transposed()
        for poly in mesh.polygons:
            normal = (normal_matrix @ poly.normal)
            if normal.length == 0.0:
                continue
            if (normal.normalized()).z < 0.9:
                continue
            corners = [matrix @ mesh.vertices[i].co for i in poly.vertices]
            if len(corners) < 3:
                continue
            # Newell area of the world-space polygon.
            total = Vector((0.0, 0.0, 0.0))
            for i, current in enumerate(corners):
                nxt = corners[(i + 1) % len(corners)]
                total += current.cross(nxt)
            area = total.length * 0.5
            if area <= 0.0:
                continue
            out.append((area, sum(c.z for c in corners) / len(corners)))
        evaluated.to_mesh_clear()
    return out


def detect_floor_z(objects, lo_z: float, hi_z: float, bucket: float = 0.02):
    """Find the walkable surface: the upward-facing plane carrying the most
    area in the lower part of the model.

    The actor stands ON the floor, so the floor's TOP surface is the height that
    belongs at z=0 -- not the bounding-box bottom, which is the underside of the
    slab and buries the actor's feet by the slab thickness.
    """
    span = hi_z - lo_z
    ceiling = lo_z + span * 0.4
    weights: dict[int, float] = {}
    for area, z in upward_faces(objects):
        if z > ceiling:
            continue
        weights[int(round(z / bucket))] = weights.get(int(round(z / bucket)), 0.0) + area
    if not weights:
        return None, 0.0
    key = max(weights, key=weights.get)
    # Refine within the winning bucket: an area-weighted mean recovers the exact
    # plane height instead of the bucket's rounded centre.
    numerator = denominator = 0.0
    for area, z in upward_faces(objects):
        if z > ceiling or int(round(z / bucket)) != key:
            continue
        numerator += area * z
        denominator += area
    exact = numerator / denominator if denominator else key * bucket
    return exact, weights[key]


def import_model(path: Path, model_height: float | None, yaw_degrees: float = 0.0,
                 floor_z: float | None = None, recenter: bool = True):
    before = {o.name for o in bpy.data.objects}
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        raise SystemExit(f"unsupported model format: {path.suffix}")

    # The importer's object matrices are not evaluated until the depsgraph
    # settles. Measuring before this reads unparented/unscaled bounds and
    # silently computes the wrong normalisation factor.
    bpy.context.view_layer.update()

    meshes = imported_meshes(before)
    if not meshes:
        raise SystemExit(f"no meshes imported from {path}")

    # Roots only, so a parented hierarchy is transformed once.
    roots = [o for o in bpy.data.objects
             if o.name not in before and o.parent is None]

    # Turn the model about Z before measuring: an image-to-3D result arrives at
    # an arbitrary yaw, and a cutaway room is only readable when its open face
    # is turned toward the camera.
    if yaw_degrees:
        spin = Matrix.Rotation(math.radians(float(yaw_degrees)), 4, "Z")
        for obj in roots:
            obj.matrix_world = spin @ obj.matrix_world
        bpy.context.view_layer.update()

    lo, hi = world_bounds(meshes)
    raw_height = hi.z - lo.z
    if raw_height <= 0:
        raise SystemExit("imported model has zero height")
    # model_height None means the model is already authored at true scale.
    scale = 1.0 if model_height is None else float(model_height) / raw_height

    # Compose matrix_world rather than assigning obj.scale: the latter does not
    # reliably propagate to matrix_world in background mode, which silently
    # leaves the model at its imported size.
    for obj in roots:
        obj.matrix_world = Matrix.Scale(scale, 4) @ obj.matrix_world
    bpy.context.view_layer.update()

    # Re-measure after scaling, then seat the floor on z=0 and centre on the
    # action plane so the Walker stands inside the room rather than beside it.
    lo, hi = world_bounds(meshes)
    centre_x = (lo.x + hi.x) * 0.5 if recenter else 0.0
    centre_y = (lo.y + hi.y) * 0.5 if recenter else 0.0

    if floor_z is None and not recenter:
        # Authored in the camera's own frame: the floor is already at z=0 and
        # moving it would discard the placement the recipe encodes.
        detected, floor_source, floor_area = 0.0, "authored", 0.0
    elif floor_z is None:
        detected, area = detect_floor_z(meshes, lo.z, hi.z)
        if detected is None:
            raise SystemExit(
                "could not find an upward-facing floor surface; pass --floor-z "
                "with the walkable height in normalised world units"
            )
        floor_source, floor_area = "detected", area
    elif True:
        detected, floor_source, floor_area = float(floor_z), "explicit", 0.0

    offset = Matrix.Translation(Vector((-centre_x, -centre_y, -detected)))
    for obj in roots:
        obj.matrix_world = offset @ obj.matrix_world
    bpy.context.view_layer.update()

    collection = bpy.data.collections.new(MODEL_COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    for obj in roots:
        for parent in list(obj.users_collection):
            parent.objects.unlink(obj)
        collection.objects.link(obj)

    lo, hi = world_bounds(meshes)
    achieved = hi.z - lo.z
    if model_height is not None and             abs(achieved - float(model_height)) > max(1e-3, float(model_height) * 1e-3):
        raise SystemExit(
            f"model normalisation failed: asked for {model_height} world units "
            f"tall, measured {achieved:.6f}. Refusing to stage a room whose "
            "scale is unknown -- the Walker ratio would be meaningless."
        )
    seated, _ = detect_floor_z(meshes, lo.z, hi.z)
    if seated is None or abs(seated) > 0.05:
        raise SystemExit(
            f"walkable floor seated at z={seated}, expected 0. The actor would "
            "stand in or above the floor."
        )
    return meshes, {
        "yawDegrees": float(yaw_degrees),
        "floorZ": detected,
        "floorSource": floor_source,
        "floorArea": floor_area,
        "belowFloor": lo.z,
        "rawHeight": raw_height,
        "appliedScale": scale,
        "achievedHeight": achieved,
        "extent": [hi.x - lo.x, hi.y - lo.y, hi.z - lo.z],
        "min": [lo.x, lo.y, lo.z],
        "max": [hi.x, hi.y, hi.z],
    }


def base_lighting(strength: float, background=(0.0, 0.0, 0.0)) -> None:
    """Diffuse baseline visibility, over a solid (by default black) backdrop.

    Two jobs that are usually conflated: the world both LIGHTS the scene and is
    what the camera sees where nothing else is. Splitting them on Is Camera Ray
    lets the void render pure black while the same world still provides even
    fill, so a room can sit on black without being lit like a diorama.

    A hard raking key is what makes an interior read as a diorama, so there is
    none here. Every hard shadow must come from a light the room itself
    contains, authored into the .blend beside the geometry that motivates it.
    """
    world = bpy.data.worlds.new("TH_WORLD")
    world.use_nodes = True
    tree = world.node_tree
    nodes, links = tree.nodes, tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    mix = nodes.new("ShaderNodeMixShader")
    path = nodes.new("ShaderNodeLightPath")

    fill = nodes.new("ShaderNodeBackground")
    fill.inputs[0].default_value = (0.62, 0.66, 0.74, 1.0)
    fill.inputs[1].default_value = float(strength)

    backdrop = nodes.new("ShaderNodeBackground")
    backdrop.inputs[0].default_value = tuple(background) + (1.0,)
    backdrop.inputs[1].default_value = 1.0

    links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
    links.new(fill.outputs[0], mix.inputs[1])
    links.new(backdrop.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    bpy.context.scene.world = world


def outdoor_sun(energy: float) -> None:
    """Opt-in hard key, for exteriors only."""
    light = bpy.data.lights.new("TH_SUN", type="SUN")
    light.energy = float(energy)
    light.angle = math.radians(2.0)
    obj = bpy.data.objects.new("TH_SUN", light)
    obj.rotation_euler = Vector((0.75, 0.35, -0.85)).normalized().to_track_quat(
        "-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(obj)


def rebind_library_materials(meshes) -> list:
    """Re-apply material-library textures to an imported model.

    OBJ/MTL cannot carry a node-based texture set, but it does carry material
    NAMES. Those names are the semantic contract (`sr_<semantic_id>`), so the
    library can supply appearance here rather than being baked into the
    interchange file.
    """
    rebound = []
    seen = set()
    for obj in meshes:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or material.name in seen:
                continue
            seen.add(material.name)
            semantic = material.name.split(".")[0]
            if not semantic.startswith("sr_"):
                continue
            semantic = semantic[3:]
            if material_library.load(semantic) is None:
                continue
            slot.material = material_library.build_material(asset_core, semantic)
            rebound.append(semantic)
    for obj in meshes:
        for slot in obj.material_slots:
            name = (slot.material.name if slot.material else "").split(".")[0]
            if name.startswith("sr_") and name[3:] in rebound:
                slot.material = bpy.data.materials.get(name, slot.material)
    return sorted(set(rebound))


def projected_pixel_span(record, meshes):
    """Half-width, in target pixels, needed to contain the model.

    A metre of lateral offset maps to `baseWidth / (2 * fovHalfX * depth)`
    TARGET pixels, which is independent of the target width -- widening the
    target reveals more world at the same texel scale rather than zooming.
    That is what makes a full-map preview honest: it is the same camera, just
    a wider window.
    """
    k = record["baseViewportWidth"] / (2.0 * record["fovHalfX"])
    eye_x = record["eye"]["x"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    worst = 0.0
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh is None:
            continue
        matrix = evaluated.matrix_world
        for vertex in mesh.vertices:
            point = matrix @ vertex.co
            depth = point.x - eye_x
            if depth <= record["nearPlane"]:
                continue
            worst = max(worst, abs(k * point.y / depth))
        evaluated.to_mesh_clear()
    return worst


def widen_record(record, target_width):
    """Same lens, same eye, wider window."""
    widened = json.loads(json.dumps(record))
    widened["targetWidth"] = int(target_width)
    widened["viewportCenterX"] = int(target_width) // 2
    return widened


def _eevee_engine() -> str:
    """EEVEE's enum id moved between Blender releases (BLENDER_EEVEE ->
    BLENDER_EEVEE_NEXT in 4.2 -> back to BLENDER_EEVEE in 5.x)."""
    available = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if candidate in available:
            return candidate
    return "BLENDER_WORKBENCH"


def measure_actor(scene, camera_obj, actor) -> dict:
    feet = actor.location.copy()
    head = feet + Vector((0.0, 0.0, WALKER_WORLD_HEIGHT))
    fx, fy = thestra_camera.project_world_point(scene, camera_obj, feet)
    hx, hy = thestra_camera.project_world_point(scene, camera_obj, head)
    return {
        "feetPx": [fx, fy],
        "headPx": [hx, hy],
        "pixelHeight": abs(fy - hy),
    }


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="stage_room_model")
    parser.add_argument("--model", type=Path, required=True,
                        help="GLB/GLTF/OBJ produced by the image-to-3D step")
    parser.add_argument("--model-height", type=float, default=None,
                        help="normalise the room to this world-unit height; a "
                             "1.75-unit Walker is the reference. Omit for a model "
                             "already authored at true metre scale.")
    parser.add_argument("--no-recenter", dest="recenter", action="store_false",
                        help="keep authored XY placement and floor height, for a "
                             "model authored in the camera's own frame")
    parser.add_argument("--camera", type=Path, default=DEFAULT_CAMERA)
    parser.add_argument("--walker", type=Path, default=DEFAULT_WALKER)
    parser.add_argument("--walker-at", type=float, default=0.0,
                        help="Walker position along the camera's forward axis")
    parser.add_argument("--yaw", type=float, default=0.0,
                        help="rotate the model about Z (degrees) so its open "
                             "cutaway face turns toward the camera")
    parser.add_argument("--ambient", type=float, default=0.55,
                        help="diffuse baseline visibility (world light)")
    parser.add_argument("--target-width", type=int, default=None,
                        help="override the target width in native px. The "
                             "game's default horizontal resolution is 256; "
                             "426 is the wide variant.")
    parser.add_argument("--full-map", action="store_true",
                        help="widen the window until the whole authored map "
                             "fits, so the preview shows where it ends")
    parser.add_argument("--background", type=float, nargs=3, default=(0.0, 0.0, 0.0),
                        metavar=("R", "G", "B"),
                        help="what the camera sees where nothing else is; "
                             "black by default, and independent of the fill")
    parser.add_argument("--sun", type=float, default=0.0,
                        help="opt-in hard sun for EXTERIORS; interiors should "
                             "take every hard shadow from authored lights")
    parser.add_argument("--floor-z", type=float, default=None,
                        help="walkable surface height in normalised world units; "
                             "overrides automatic floor detection")
    parser.add_argument("--no-materials", dest="materials", action="store_false",
                        help="skip material-library rebinding and keep raw MTL")
    parser.add_argument("--engine", choices=("eevee", "workbench", "cycles"),
                        default="eevee")
    parser.add_argument("--out", type=Path, default=None, help="save a .blend")
    parser.add_argument("--render", type=Path, default=None, help="render a 426x240 PNG")
    parser.add_argument("--tolerance", type=float, default=0.5,
                        help="allowed Walker pixel-height error")
    args = parser.parse_args(argv)

    source_is_blend = args.model.suffix.lower() == ".blend"
    if source_is_blend:
        # The .blend is SOURCE AUTHORITY: open it and never save it. Its own
        # materials and canonical lights are the point of using it.
        bpy.ops.wm.open_mainfile(filepath=str(args.model.resolve()))
        # Drop any camera/actor left by a previous staging BEFORE building the
        # calibrated pair, or the cleanup would delete what it just made.
        for name in (thestra_camera.CAMERA_NAME, thestra_camera.ACTOR_NAME):
            stale = bpy.data.objects.get(name)
            if stale is not None:
                bpy.data.objects.remove(stale, do_unlink=True)
    else:
        reset_scene()
    scene = bpy.context.scene

    record = thestra_camera.load_calibration(str(args.camera))
    if args.target_width:
        record = widen_record(record, args.target_width)
    camera = thestra_camera.create_or_update_camera(record, scene=scene,
                                                    make_active=True)

    # A mirrored (determinant -1) camera basis cannot survive the
    # to_quaternion() conversion inside create_actor_preview, and silently
    # flips the actor. Refuse rather than render an upside-down character.
    determinant = camera.matrix_world.to_3x3().determinant()
    if determinant < 0.0:
        raise SystemExit(
            f"camera basis is mirrored (determinant {determinant:+.4f}). "
            "right must equal forward x up; with forward +X and up +Z that "
            "means rightY = -1. Fix the calibration record."
        )

    # A mirrored (determinant -1) camera basis cannot survive the
    # to_quaternion() conversion inside create_actor_preview, and silently
    # flips the actor. Refuse rather than render an upside-down character.
    determinant = camera.matrix_world.to_3x3().determinant()
    if determinant < 0.0:
        raise SystemExit(
            f"camera basis is mirrored (determinant {determinant:+.4f}). "
            "right must equal forward x up; with forward +X and up +Z that "
            "means rightY = -1. Fix the calibration record."
        )

    if source_is_blend:
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        if not meshes:
            raise SystemExit(f"{args.model} contains no mesh geometry")
        lo, hi = world_bounds(meshes)
        model_info = {"source": "blend", "appliedScale": 1.0,
                      "extent": [hi.x - lo.x, hi.y - lo.y, hi.z - lo.z],
                      "min": [lo.x, lo.y, lo.z], "max": [hi.x, hi.y, hi.z]}
    else:
        meshes, model_info = import_model(args.model, args.model_height, args.yaw,
                                          args.floor_z, args.recenter)
    rebound = ([] if source_is_blend
               else rebind_library_materials(meshes) if args.materials else [])
    base_lighting(args.ambient, args.background)
    lights = sorted(o.name for o in bpy.data.objects if o.type == "LIGHT")
    if args.sun:
        outdoor_sun(args.sun)

    actor = thestra_camera.create_actor_preview(
        str(args.walker), camera,
        anchor=(float(args.walker_at), 0.0, 0.0),
        frame_width=24, frame_height=48, frame_index=0,
        world_height=WALKER_WORLD_HEIGHT,
    )
    bpy.context.view_layer.update()

    if args.full_map:
        # Re-solve the camera against a window wide enough to hold the whole
        # authored map, so a preview shows where the map actually ENDS. An
        # interior that runs off the frame edge promises the player another
        # screen; the preview has to make that promise checkable.
        needed = int(math.ceil(projected_pixel_span(record, meshes) * 2.0)) + 8
        record = widen_record(record, max(needed, record["targetWidth"]))
        camera = thestra_camera.create_or_update_camera(record, scene=scene,
                                                        make_active=True)
        actor.rotation_quaternion = camera.matrix_world.to_quaternion()
        bpy.context.view_layer.update()

    actor_info = measure_actor(scene, camera, actor)
    error = abs(actor_info["pixelHeight"] - WALKER_NATIVE_PIXELS)

    # characterFloorLimit bounds CHARACTER PLACEMENT, not the scene. The set
    # itself must keep filling the frame past it -- floor extension, foreground
    # and outdoor ground all belong below the limit.
    floor_limit = float(record.get("thestraComposition", {}).get(
        "characterFloorLimit", scene.render.resolution_y))
    feet_y, head_y = actor_info["feetPx"][1], actor_info["headPx"][1]
    actor_info["characterFloorLimit"] = floor_limit
    actor_info["headroomAboveLimit"] = floor_limit - feet_y
    if feet_y > floor_limit:
        raise SystemExit(
            f"Walker feet project to y={feet_y:.1f}, below the character floor "
            f"limit of {floor_limit:g}px; the engine would need Y camera "
            "scrolling. Fix the camera record, not the model."
        )
    if head_y < 0.0:
        raise SystemExit(f"Walker head projects to y={head_y:.1f}, above the frame")

    report = {
        "camera": str(args.camera),
        "model": str(args.model),
        "modelHeight": args.model_height,
        "modelInfo": model_info,
        "actor": actor_info,
        "expectedPixelHeight": WALKER_NATIVE_PIXELS,
        "pixelHeightError": error,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "targetWidth": record["targetWidth"],
        "materialsRebound": rebound,
        "authoredLights": lights,
    }

    if args.render:
        render_path = args.render.resolve()
        render_path.parent.mkdir(parents=True, exist_ok=True)
        # Blender resolves a relative render path against the drive root, not
        # the working directory; always hand it an absolute path.
        scene.render.filepath = str(render_path)
        scene.render.image_settings.file_format = "PNG"
        scene.render.engine = (_eevee_engine() if args.engine == "eevee"
                               else "BLENDER_WORKBENCH" if args.engine == "workbench"
                               else "CYCLES")
        scene.render.film_transparent = False
        bpy.ops.render.render(write_still=True)
        report["render"] = str(render_path)
        report["engine"] = scene.render.engine

    if args.out and source_is_blend:
        raise SystemExit("refusing to write a .blend from a .blend source; the "
                         "source document is authority and staging never saves it")
    if args.out:
        blend_path = args.out.resolve()
        blend_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        report["blend"] = str(blend_path)

    print("STAGE ROOM BEGIN")
    print(json.dumps(report, indent=2))
    print("STAGE ROOM END")

    if error > args.tolerance:
        raise SystemExit(
            f"Walker projects to {actor_info['pixelHeight']:.3f}px, expected "
            f"{WALKER_NATIVE_PIXELS}px (error {error:.3f}px). The fixed "
            "character pixel scale is broken -- the camera record is wrong, "
            "not the model."
        )


if __name__ == "__main__":
    main()
