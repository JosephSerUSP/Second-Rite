"""Photograph the first grammar-generated building as CLAY, against the real camera.

This is a topology pass, not a material pass.  Every surface is overridden with
one neutral clay, because a grammar can only be judged on massing once the
whitewash-and-azulejo palette stops doing the reading for it -- a decorated box
and a piece of architecture look alike under texture and nothing alike under
clay.

Two things here are not optional and are the reason the script exists at all:

* **The camera is the fixture, unmodified.**  `fixtures/town_sideview_camera.json`
  is the same camera the game draws with, so a building that reads here reads in
  play.  The only frame that departs from it is the explicitly-labelled
  three-quarter study, which rotates the eye about the action plane on a circle
  of the solved radius -- the pixel scale at the action plane is therefore
  unchanged, and the frame is a plan-legibility check rather than a new camera.
* **There is a walker in every frame.**  A frame-fraction metric cannot see that
  a building dwarfs a person, and two earlier authoring passes went wrong for
  exactly that reason.  The walker is the 1.75 m billboard whose feet land on
  scanline 128 and which therefore reads 48 px tall; if it looks like a mouse at
  the door, that is the finding.

The building sits on the authored terrace line (``--back-x`` 9.0, the
`Exterior` default) rather than on the action plane.  Put its façade at X = 0
and the projecting cornice lands in FRONT of the plane, where the tall-or-
continuous rule correctly classifies the whole body as a BOARD.

Nothing here opens or writes a .blend.  The scene is built from scratch in a
factory-startup session and only PNGs leave it.

    blender --background --factory-startup --python tools/blender/study_house_grammar.py -- --out DIR
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

import thestra_camera  # noqa: E402
import wide_screen  # noqa: E402
from exterior import Exterior  # noqa: E402
from house_grammar import staging  # noqa: E402
from house_grammar.emit_blender import emit, object_name  # noqa: E402
from house_grammar.library import narrow_townhouse  # noqa: E402
from house_grammar.recipe import build  # noqa: E402

DEFAULT_OUT = Path(r"C:\Users\josep\AppData\Local\Temp\claude"
                   r"\D--Antigravity-Hichaukitoden"
                   r"\90c12529-2230-45cd-8f00-3225f56c112a\scratchpad\house_study")
WALKER_SHEET = ROOT / "projects/hichaukitoden-game/assets/character/town/npc_alicia.png"

# The lane the study is authored on.  24 m is wide enough to hold the townhouse
# plus a neighbour on each side without either neighbour reaching a lane end,
# where the wide frame's half-screen margin would show void instead of street.
SPAN = 24.0
NEIGHBOUR_OFFSET = 5.6
# Review scale.  Integer and nearest-neighbour: any resampling invents edges,
# and edges are the entire subject of a clay pass at 256x240.
UPSCALE = 3


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="study_house_grammar")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--back-x", type=float, default=9.0,
                        help="terrace line; the Exterior default, not a free knob")
    parser.add_argument("--lane-y", type=float, default=SPAN / 2.0)
    return parser.parse_args(values)


def clay_material():
    """One neutral dielectric for the whole scene.

    Mid grey rather than white: a white clay blows out under the sky dome and
    loses the very shading gradient that tells a recess from a projection.
    """
    material = bpy.data.materials.new("STUDY_clay")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.58, 0.56, 0.53, 1.0)
    principled.inputs["Roughness"].default_value = 0.82
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.25
    return material


def override_with_clay(material):
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.material_index = 0


def sky_world():
    """A pale sky behind the building.

    On black the roofline silhouette is unreadable, and the silhouette is most
    of what a massing pass is looking at.
    """
    world = bpy.data.worlds.new("STUDY_SKY")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.52, 0.63, 0.78, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world


def eevee_engine():
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        if name in items:
            return name
    raise RuntimeError("no EEVEE engine in this Blender build")


def rotated_record(record, degrees):
    """The fixture camera swung around the action plane, distance preserved.

    The eye orbits the origin on the solved radius, so a 1.75 m figure standing
    at the action plane still reads 48 px.  This is the same lens seen from a
    different bearing, not a second calibration.
    """
    turned = json.loads(json.dumps(record))
    theta = math.radians(degrees)
    cos, sin = math.cos(theta), math.sin(theta)
    eye_x, eye_y = float(record["eye"]["x"]), float(record["eye"]["y"])
    turned["eye"]["x"] = eye_x * cos - eye_y * sin
    turned["eye"]["y"] = eye_x * sin + eye_y * cos
    # Rotating both basis vectors by the same angle keeps the determinant of the
    # basis positive; flipping only one is the mirrored basis of issue #935.
    turned["orientation"]["forwardX"] = cos
    turned["orientation"]["forwardY"] = sin
    turned["orientation"]["rightX"] = sin
    turned["orientation"]["rightY"] = -cos
    return turned


def column_matched_y(scene, camera, target, plane_x=0.0):
    """Action-plane Y that lands on the same screen column as ``target``.

    "Beside the door" cannot mean "at the door's Y": the player walks the action
    plane and the façade is metres behind it, so equal world Y puts the figure
    visibly off the doorway.  Screen column is linear in world Y at a fixed
    depth, so two probes solve it exactly.
    """
    wanted = thestra_camera.project_world_point(scene, camera, target)[0]
    low = thestra_camera.project_world_point(scene, camera, Vector((plane_x, 0.0, 0.0)))[0]
    high = thestra_camera.project_world_point(scene, camera, Vector((plane_x, 1.0, 0.0)))[0]
    return (wanted - low) / (high - low)


def stage_walker(camera, name, scene_y):
    obj = thestra_camera.create_actor_preview(
        WALKER_SHEET, camera, anchor=(0.0, scene_y, 0.0),
        world_height=staging.WALKER_HEIGHT_M, name=name)
    obj.hide_render = False
    return obj


def upscale_nearest(source, target, factor):
    """Integer nearest-neighbour blow-up, done on the pixel buffer.

    ``Image.scale`` filters, and a filtered review frame lies about which edges
    the renderer actually produced.  Both images are read and written as
    Non-Color so the round trip is byte-for-byte the rendered value.
    """
    image = bpy.data.images.load(str(source))
    image.colorspace_settings.name = "Non-Color"
    width, height = image.size
    pixels = list(image.pixels)
    out = []
    for row in range(height):
        line = pixels[row * width * 4:(row + 1) * width * 4]
        wide = []
        for column in range(width):
            wide.extend(line[column * 4:column * 4 + 4] * factor)
        out.extend(wide * factor)
    scaled = bpy.data.images.new(target.stem, width * factor, height * factor,
                                 alpha=True)
    scaled.colorspace_settings.name = "Non-Color"
    scaled.pixels = out
    scaled.file_format = "PNG"
    scaled.filepath_raw = str(target)
    scaled.save()
    # The spread of the native buffer is the blank check: a frame that failed to
    # light or missed the set is one flat colour and says so here.
    channels = [pixels[index::4] for index in range(3)]
    bpy.data.images.remove(image)
    bpy.data.images.remove(scaled)
    return {"nativeMin": round(min(min(c) for c in channels), 4),
            "nativeMax": round(max(max(c) for c in channels), 4)}


def render_frame(scene, out_dir, label):
    native = out_dir / ("%s.png" % label)
    scene.render.filepath = str(native)
    bpy.ops.render.render(write_still=True)
    spread = upscale_nearest(native, out_dir / ("%s_x%d.png" % (label, UPSCALE)),
                             UPSCALE)
    return {"label": label, "native": str(native),
            "scaled": str(out_dir / ("%s_x%d.png" % (label, UPSCALE))),
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "bytes": native.stat().st_size, **spread}


def main():
    options = parse_args()
    out_dir = options.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    recipe = narrow_townhouse()
    records = build(recipe)

    exterior = Exterior("house_study", SPAN, back_x=options.back_x)
    exterior.ground()
    exterior.sky_rig()
    sky_world()

    result = emit(records, name=recipe.id, collection=bpy.context.collection,
                  back_x=options.back_x, lane_y=options.lane_y,
                  exterior=exterior, recipe=recipe)

    # Blank flanking masses, shown only in the wide frame.  Their whole job is
    # to answer one question: does the townhouse read as its own building, or
    # does it dissolve into a terrace the moment it has neighbours?
    neighbours = []
    for index, offset in enumerate((-NEIGHBOUR_OFFSET, NEIGHBOUR_OFFSET)):
        wing = recipe.wing("main")
        neighbours.append(exterior.part(
            "STUDY_neighbour_%d" % index, (wing.depth, 4.60, 8.20),
            (options.back_x + wing.depth / 2.0,
             exterior.y(options.lane_y + offset), 4.10),
            exterior.stone))

    override_with_clay(clay_material())

    scene = bpy.context.scene
    scene.render.engine = eevee_engine()
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filter_size = 0.0  # a clay pass judges edges, so do not soften them

    camera_record = staging.camera_record()
    door = recipe.openings[0]
    lane_centre = exterior.lane_centre
    centre_y = lane_centre - options.lane_y

    # The door's Y is read off the EMITTED object, not predicted.
    # `staging.place()` mirrors a record's local +Y to the lower scene Y;
    # `emit_blender.emit()` applies only the lane conversion and leaves local Y
    # alone.  The two therefore disagree in sign for anything asymmetric -- the
    # symmetric body and roof hide it, the door does not.  Neither module is
    # this study's to fix, so the walker is staged against what is actually in
    # the scene and both numbers are reported.
    door_obj = bpy.data.objects[object_name("STUDY_", recipe.id, door.role)]
    # A parent transform assigned in this session is not in `matrix_world` until
    # the view layer is evaluated, and a background run never evaluates it on
    # its own -- without this the door measures a confident, wrong 0.0.
    bpy.context.view_layer.update()
    door_ys = [(door_obj.matrix_world @ vertex.co).y
               for vertex in door_obj.data.vertices]
    door_y = (min(door_ys) + max(door_ys)) / 2.0
    predicted_door_y = staging.place(
        [record for record in records if record.role == door.role][0],
        back_x=options.back_x, lane_y=options.lane_y, lane_centre=lane_centre)
    predicted_door_y = (predicted_door_y[0][1] + predicted_door_y[1][1]) / 2.0

    for obj in neighbours:
        obj.hide_render = True

    frames = []
    camera = thestra_camera.create_or_update_camera(camera_record, scene=scene,
                                                    make_active=True)
    walker = stage_walker(camera, "STUDY_WALKER", centre_y - 2.4)
    frames.append(render_frame(scene, out_dir, "01_screen_centred"))

    door_point = Vector((options.back_x, door_y, door.height / 2.0))
    walker.location.y = column_matched_y(scene, camera, door_point)
    frames.append(render_frame(scene, out_dir, "02_screen_door"))

    # The measurement that keeps the whole sheet honest, taken through the
    # renderer's own projection rather than recomputed.
    feet = thestra_camera.project_world_point(scene, camera, walker.location)
    head = thestra_camera.project_world_point(
        scene, camera, walker.location + Vector((0.0, 0.0, staging.WALKER_HEIGHT_M)))
    walker_px = abs(head[1] - feet[1])

    # Swinging the eye alone slides the whole street out of frame, because the
    # façade sits 9 m behind the pivot. Principal-point compensation puts the
    # building's front centre back on the column it occupied head-on -- the same
    # trick `study_town_pitch.py` uses vertically, and it changes framing only:
    # eye, lens and walker scale are untouched.
    facade_centre = Vector((options.back_x, centre_y, 0.0))
    head_on_column = thestra_camera.project_world_point(scene, camera, facade_centre)[0]
    turned = rotated_record(camera_record, 34.0)
    camera = thestra_camera.create_or_update_camera(turned, scene=scene, make_active=True)
    turned["viewportCenterX"] += head_on_column - thestra_camera.project_world_point(
        scene, camera, facade_centre)[0]
    camera = thestra_camera.create_or_update_camera(turned, scene=scene, make_active=True)
    # The walker keeps the world position it held head-on. Re-matching it to the
    # door's new column would drag it metres toward the eye and it would stop
    # reading 48 px, which is the one thing this figure is here to do.
    walker.rotation_quaternion = camera.matrix_world.to_quaternion()
    frames.append(render_frame(scene, out_dir, "03_three_quarter"))

    for obj in neighbours:
        obj.hide_render = False
    ppu = float(camera_record["thestraComposition"]["pixelsPerWorldUnit"])
    wide = wide_screen.widened_record(camera_record, target_width=int(round(SPAN * ppu)),
                                      lane_x=0.0, centre_y=centre_y)
    camera = thestra_camera.create_or_update_camera(wide, scene=scene, make_active=True)
    walker.rotation_quaternion = camera.matrix_world.to_quaternion()
    # A second figure at the far end: one walker proves scale at the door, two
    # prove the street does not grow a different scale as it recedes sideways.
    stage_walker(camera, "STUDY_WALKER_FAR", centre_y - NEIGHBOUR_OFFSET - 3.2)
    frames.append(render_frame(scene, out_dir, "04_wide_neighbours"))

    body = records[0]
    report = {
        "recipe": recipe.id, "backX": options.back_x, "laneY": options.lane_y,
        "readableSize": staging.readable_size(body, back_x=options.back_x,
                                              lane_y=options.lane_y,
                                              lane_centre=lane_centre),
        "boards": staging.boards(records, back_x=options.back_x,
                                 lane_y=options.lane_y, lane_centre=lane_centre),
        "dockCoverage": staging.dock_coverage(records, back_x=options.back_x,
                                              lane_y=options.lane_y,
                                              lane_centre=lane_centre),
        "walkerMeasuredPx": round(walker_px, 2),
        "walkerFeetRow": round(feet[1], 2),
        "doorSceneY": round(door_y, 3),
        "doorSceneYPredictedByStaging": round(predicted_door_y, 3),
        "records": [{"role": record.role, "vertices": len(record.vertices),
                     "faces": len(record.faces)} for record in records],
        "frames": frames,
    }
    print("STUDY " + json.dumps(report))


if __name__ == "__main__":
    main()
