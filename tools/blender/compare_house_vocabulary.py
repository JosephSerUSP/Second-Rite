"""Render a fixed-camera comparison of the owner house and veranda grammar.

This is an inspection aid, not an exporter. It loads the adopted owner source
read-only, emits two grammar compositions in a scratch Blender session, and
writes only PNG/JSON review artifacts. The fixed camera, actor scale, and lane
positions make the structural difference inspectable without turning a render
into a numerical pass/fail claim.

Example::

    blender --background --factory-startup \
      --python tools/blender/compare_house_vocabulary.py -- \
      --out out/house-vocabulary-comparison
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import replace
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

import thestra_camera  # noqa: E402
import wide_screen  # noqa: E402
from exterior import Exterior  # noqa: E402
from house_grammar import library, staging  # noqa: E402
from house_grammar.emit_blender import emit  # noqa: E402
from house_grammar.recipe import VerandaSpec, build  # noqa: E402

SEED = 7087697
SOURCE_DEFAULT = (ROOT / "projects/hichaukitoden-game/assets/authoring/environments"
                  / "st_maria_praca_modelled.blend")
WALKER = ROOT / "projects/hichaukitoden-game/assets/character/npc_alicia.png"
LANES = (4.2, 12.0, 19.8)
BACK_X = 9.0
SPAN = 24.0


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="compare_house_vocabulary")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    return parser.parse_args(values)


def world_sky():
    world = bpy.data.worlds.new("HOUSE_COMPARISON_SKY")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.52, 0.63, 0.78, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world


def eevee_engine():
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if name in items:
            return name
    raise RuntimeError("no EEVEE engine in this Blender build")


def load_owner_reference(path, collection):
    """Append the measured owner body without saving or changing its source."""
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (source, target):
        target.objects = [name for name in source.objects
                          if name == "ARCH_west_house"]
    if not target.objects:
        raise RuntimeError("owner source has no ARCH_west_house")
    owner = target.objects[0]
    collection.objects.link(owner)
    owner.name = "OWNER_ARCH_west_house"
    owner.location = (BACK_X, 0.0, 0.0)
    return owner


def clay_material():
    material = bpy.data.materials.new("HOUSE_COMPARISON_CLAY")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.58, 0.56, 0.53, 1.0)
    shader.inputs["Roughness"].default_value = 0.82
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = 0.25
    return material


def override_objects(objects, material):
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.material_index = 0


def rotated_record(record, degrees):
    turned = json.loads(json.dumps(record))
    theta = math.radians(degrees)
    cos, sin = math.cos(theta), math.sin(theta)
    eye_x, eye_y = float(record["eye"]["x"]), float(record["eye"]["y"])
    turned["eye"]["x"] = eye_x * cos - eye_y * sin
    turned["eye"]["y"] = eye_x * sin + eye_y * cos
    turned["orientation"]["forwardX"] = cos
    turned["orientation"]["forwardY"] = sin
    turned["orientation"]["rightX"] = sin
    turned["orientation"]["rightY"] = -cos
    return turned


def stage_actor(camera, exterior, lane_y, name):
    actor = thestra_camera.create_actor_preview(
        WALKER, camera, anchor=(0.0, exterior.y(lane_y), 0.0),
        world_height=staging.WALKER_HEIGHT_M, name=name)
    actor.hide_render = False
    return actor


def render(scene, output, label):
    path = output / (label + ".png")
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"label": label, "path": str(path.resolve()),
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "bytes": path.stat().st_size}


def main():
    options = parse_args()
    random.seed(SEED)
    output = options.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    collection = scene.collection

    exterior = Exterior("house_vocabulary_comparison", SPAN, back_x=BACK_X)
    exterior.ground()
    exterior.sky_rig()
    world_sky()

    owner = load_owner_reference(options.source, collection)
    # The source object is a measured reference, not a generated replacement.
    owner.location.y = exterior.y(LANES[2])

    base = library.canopy_steps_house()
    veranda = VerandaSpec(
        id="front_gallery", wing="main", lane_offset=-0.25,
        width=4.65, depth=1.15, height=2.55, roof_rise=0.24,
        roof_thickness=0.14, slab=0.16, support_count=3,
        support_width=0.16)
    composed = replace(base, id="canopy_steps_veranda",
                       attachments=(veranda,))
    generated = []
    for recipe, lane_y, label in ((base, LANES[0], "GRAMMAR_BASE"),
                                  (composed, LANES[1], "GRAMMAR_VERANDA")):
        result = emit(build(recipe), name=label, collection=collection,
                      lane_y=lane_y, back_x=BACK_X, exterior=exterior,
                      namespace="COMPARE_", recipe=recipe)
        generated.extend(bpy.data.objects[name]
                         for name in result["objects"]
                         if bpy.data.objects[name].type == "MESH")

    camera_record = staging.camera_record()
    ppu = float(camera_record["thestraComposition"]["pixelsPerWorldUnit"])
    wide = wide_screen.widened_record(
        camera_record, target_width=int(round(SPAN * ppu)), lane_x=0.0,
        centre_y=exterior.y(SPAN / 2.0))
    camera = thestra_camera.create_or_update_camera(
        wide, scene=scene, make_active=True)
    actors = [stage_actor(camera, exterior, lane, "WALKER_%d" % index)
              for index, lane in enumerate(LANES)]

    scene.render.engine = eevee_engine()
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.0
    frames = [render(scene, output, "01_materials_wide")]

    clay = clay_material()
    override_objects([owner] + generated, clay)
    frames.append(render(scene, output, "02_clay_wide"))

    # A fixed three-quarter view tests whether the veranda reads as depth and
    # attachment rather than as a painted strip. The actor remains in frame.
    turned = rotated_record(camera_record, 34.0)
    turned["targetWidth"] = wide["targetWidth"]
    turned["viewportCenterX"] = wide["viewportCenterX"]
    turned["viewportCenterY"] = wide["viewportCenterY"]
    camera = thestra_camera.create_or_update_camera(
        turned, scene=scene, make_active=True)
    for actor in actors:
        actor.rotation_quaternion = camera.matrix_world.to_quaternion()
    frames.append(render(scene, output, "03_clay_three_quarter"))

    action_plane = Vector((0.0, exterior.y(LANES[1]), 0.0))
    feet = thestra_camera.project_world_point(scene, camera, action_plane)[1]
    head = thestra_camera.project_world_point(
        scene, camera, action_plane + Vector((0.0, 0.0, staging.WALKER_HEIGHT_M)))[1]
    report = {
        "seed": SEED, "source": str(options.source.resolve()),
        "sourceObject": "ARCH_west_house", "camera": "town_sideview_camera",
        "cameraView": ("wide fixed projection; three-quarter is explicitly "
                       "a perspective study"),
        "actorHeightMetres": staging.WALKER_HEIGHT_M,
        "actorMeasuredPixelsThreeQuarter": round(abs(head - feet), 2),
        "lanes": list(LANES), "backX": BACK_X,
        "compositions": [base.id, composed.id],
        "newControls": {"attachment": "front_gallery", "width": veranda.width,
                         "depth": veranda.depth, "supportCount": veranda.support_count},
        "frames": frames,
        "limits": [
            "The owner mesh is a reference silhouette; this is not pixel parity.",
            "Materials are runtime vocabulary materials, not a source bake.",
            "The three-quarter image is a plan/depth study, not the canon town view.",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                        encoding="utf-8")
    print("HOUSE COMPARISON " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
