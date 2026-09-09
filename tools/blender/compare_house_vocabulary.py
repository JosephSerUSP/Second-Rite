"""Render inspectable house-vocabulary authoring studies.

This is not an exporter or a pixel-parity gate. It loads the adopted modelled
Praca source read-only, emits several grammar compositions in a scratch scene,
and writes only PNG/JSON review artifacts. Each frame contains one building,
one fixed camera treatment, and a 1.75 m actor for scale.

Example::

    blender --background --factory-startup \
      --python tools/blender/compare_house_vocabulary.py -- \
      --out out/house-vocabulary-comparison
"""

from __future__ import annotations

import argparse
import hashlib
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
LANE_Y = 12.0
BACK_X = 12.0
SPAN = 24.0
STUDY_WIDTH = 426


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="compare_house_vocabulary")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    return parser.parse_args(values)


def eevee_engine():
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if name in items:
            return name
    raise RuntimeError("no EEVEE engine in this Blender build")


def studio_material(name, colour, roughness=0.82):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*colour, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*colour, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = 0.25
    return material


def setup_studio(scene, exterior, lane_world_y):
    """Neutral lit studio: no fog, no sun, and no textured ground takeover."""
    world = bpy.data.worlds.new("HOUSE_COMPARISON_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.16, 0.19, 0.24, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    scene.world = world

    floor_material = studio_material(
        "HOUSE_COMPARISON_FLOOR", (0.18, 0.20, 0.23), roughness=0.9)
    floor = exterior.part(
        "HOUSE_COMPARISON_FLOOR", (11.0, 11.0, 0.08),
        (BACK_X + 2.5, lane_world_y, -0.04), floor_material)
    floor.hide_render = False

    def area(name, location, energy, size):
        light_data = bpy.data.lights.new(name, type="AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((BACK_X, lane_world_y, 2.2)) -
                                light.location).to_track_quat("-Z", "Y").to_euler()

    area("HOUSE_COMPARISON_KEY", (-3.0, lane_world_y - 7.0, 11.0), 850.0, 7.0)
    area("HOUSE_COMPARISON_FILL", (8.0, lane_world_y + 8.0, 6.0), 500.0, 9.0)
    return floor


def load_source_objects(path, collection):
    """Load source meshes for inspection without saving or modifying the file."""
    names = ("ARCH_west_house", "ARCH_roof", "BUILD_door1", "BUILD_window1")
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (source, target):
        target.objects = [name for name in names if name in source.objects]
    loaded = {obj.name: obj for obj in target.objects if obj is not None}
    missing = sorted(set(names) - set(loaded))
    if missing:
        raise RuntimeError("owner source is missing: " + ", ".join(missing))
    for obj in loaded.values():
        collection.objects.link(obj)
        obj.hide_render = True
    return loaded


def source_inspection(path, loaded):
    features = {}
    for name, obj in loaded.items():
        # Use mesh-local bounds for provenance. Object dimensions can include
        # the source file's parenting hierarchy; the recorded measurements are
        # the authored mesh vocabulary itself.
        coordinates = [vertex.co for vertex in obj.data.vertices]
        features[name] = {
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "dimensions": [round(float(max(axis) - min(axis)), 3)
                           for axis in zip(*coordinates)],
            "materials": [mat.name for mat in obj.data.materials if mat is not None],
        }
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "objects": features,
        "repository": {
            "preservationCommit": "a52a411c",
            "preservationCommitTitle": (
                "feat: preserve the modelled Praca source at its own path (#1021)"),
            "authority": (
                "Repository provenance establishes this as an adopted modelled "
                "source; object names alone are not treated as proof of human "
                "authorship."),
        },
        "motivation": [
            "ARCH_west_house is the measured 42-vertex/29-face masonry body "
            "with mirrored X/Y corner language and non-axis-aligned faces.",
            "ARCH_roof is the separate shallow overhanging gable mass.",
            "BUILD_door1 and BUILD_window1 show projecting, layered opening "
            "assemblies; canopy/steps already exist in the grammar.",
            "A continuous house-wide covered gallery is not present in the "
            "existing records, so the veranda is an explicit composable extension, "
            "not a claim to reconstruct an unseen source feature.",
        ],
    }


def clay_material():
    return studio_material("HOUSE_COMPARISON_CLAY", (0.58, 0.56, 0.53))


def override_objects(objects, material):
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.material_index = 0


def rotated_record(record, degrees, pivot_y):
    turned = json.loads(json.dumps(record))
    theta = math.radians(degrees)
    cos, sin = math.cos(theta), math.sin(theta)
    eye_x = float(record["eye"]["x"])
    eye_y = float(record["eye"]["y"]) - pivot_y
    turned["eye"]["x"] = eye_x * cos - eye_y * sin
    turned["eye"]["y"] = eye_x * sin + eye_y * cos + pivot_y
    turned["orientation"]["forwardX"] = cos
    turned["orientation"]["forwardY"] = sin
    turned["orientation"]["rightX"] = sin
    turned["orientation"]["rightY"] = -cos
    return turned


def frame_camera(scene, camera_record, pivot_y, *, angle=0.0,
                 width=STUDY_WIDTH, base_row=184.0):
    record = wide_screen.widened_record(
        camera_record, target_width=width, lane_x=0.0, centre_y=pivot_y)
    if angle:
        record = rotated_record(record, angle, pivot_y)
    camera = thestra_camera.create_or_update_camera(
        record, scene=scene, make_active=True)
    target = Vector((BACK_X, pivot_y, 0.0))
    # Rotating around the action plane also rotates the building's depth
    # offset. Recenter the principal point on the building after the swing;
    # otherwise a side elevation can be perfectly projected but entirely
    # outside this fixed-width review frame.
    current_column = thestra_camera.project_world_point(
        scene, camera, target)[0]
    record["viewportCenterX"] += width / 2.0 - current_column
    camera = thestra_camera.create_or_update_camera(
        record, scene=scene, make_active=True)
    current_row = thestra_camera.project_world_point(scene, camera, target)[1]
    record["viewportCenterY"] += base_row - current_row
    camera = thestra_camera.create_or_update_camera(
        record, scene=scene, make_active=True)
    return camera, record


def stage_actor(camera, world_y, name):
    actor = thestra_camera.create_actor_preview(
        WALKER, camera, anchor=(0.0, world_y, 0.0),
        world_height=staging.WALKER_HEIGHT_M, name=name)
    actor.hide_render = True
    return actor


def render(scene, output, label):
    path = output / (label + ".png")
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"label": label, "path": str(path.resolve()),
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "bytes": path.stat().st_size}


def set_visible(active, all_house_objects, actor):
    active = set(active)
    for obj in all_house_objects:
        obj.hide_render = obj not in active
    for candidate in bpy.data.objects:
        if candidate.name.startswith("HOUSE_WALKER_"):
            candidate.hide_render = candidate is not actor


def measure_actor(scene, camera, world_y):
    feet = thestra_camera.project_world_point(
        scene, camera, Vector((0.0, world_y, 0.0)))[1]
    head = thestra_camera.project_world_point(
        scene, camera, Vector((0.0, world_y, staging.WALKER_HEIGHT_M)))[1]
    return round(abs(head - feet), 2), round(feet, 2)


def emit_variant(exterior, recipe, name, collection, all_house_objects):
    result = emit(build(recipe), name=name, collection=collection,
                  lane_y=LANE_Y, back_x=BACK_X, exterior=exterior,
                  namespace="COMPARE_", recipe=recipe)
    objects = [bpy.data.objects[obj_name] for obj_name in result["objects"]
               if bpy.data.objects[obj_name].type == "MESH"]
    all_house_objects.extend(objects)
    return objects


def main():
    options = parse_args()
    random.seed(SEED)
    output = options.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = eevee_engine()
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.0

    exterior = Exterior("house_vocabulary_comparison", SPAN, back_x=BACK_X)
    world_y = exterior.y(LANE_Y)
    setup_studio(scene, exterior, world_y)
    loaded = load_source_objects(options.source, scene.collection)
    source_report = source_inspection(options.source, loaded)
    source = loaded["ARCH_west_house"]
    source_roof = loaded["ARCH_roof"]
    source.location = (BACK_X, world_y, 0.0)
    # The adopted source keeps ARCH_roof parented to ARCH_west_house. Clear
    # that relationship in the scratch scene before placing both objects at
    # the same review origin; otherwise the parent's original offset is added
    # a second time. This never writes back to the source blend.
    source_roof.parent = None
    source_roof.location = (BACK_X, world_y, 0.0)
    source_group = [source, source_roof]
    all_house_objects = list(source_group)

    base = library.canopy_steps_house()
    shallow = replace(base, id="canopy_steps_veranda_shallow", attachments=(
        VerandaSpec("shallow_gallery", "main", lane_offset=-0.25,
                    width=4.4, depth=0.85, height=2.5,
                    roof_rise=0.18, support_count=2, support_width=0.16),))
    deep = replace(base, id="canopy_steps_veranda_deep", attachments=(
        VerandaSpec("deep_gallery", "main", lane_offset=-0.25,
                    width=4.65, depth=1.5, height=2.55,
                    roof_rise=0.28, support_count=4, support_width=0.16),))
    side = replace(base, id="canopy_steps_veranda_side", attachments=(
        VerandaSpec("side_gallery", "main", elevation="left", lane_offset=2.6,
                    width=3.7, depth=1.1, height=2.5,
                    roof_rise=0.22, support_count=2, support_width=0.16),))
    variants = {
        "base": emit_variant(exterior, base, "BASE_UNCHANGED", scene.collection,
                              all_house_objects),
        "shallow": emit_variant(exterior, shallow, "VERANDA_SHALLOW",
                                 scene.collection, all_house_objects),
        "deep": emit_variant(exterior, deep, "VERANDA_DEEP", scene.collection,
                             all_house_objects),
        "side": emit_variant(exterior, side, "VERANDA_SIDE", scene.collection,
                             all_house_objects),
    }

    camera_record = staging.camera_record()
    initial_camera, _ = frame_camera(
        scene, camera_record, world_y, width=STUDY_WIDTH)
    actors = {
        "front": stage_actor(initial_camera, world_y, "HOUSE_WALKER_FRONT"),
        "side": stage_actor(initial_camera, world_y, "HOUSE_WALKER_SIDE"),
    }
    clay = clay_material()
    frames = []

    def study(label, active_key, *, angle=0.0, width=STUDY_WIDTH,
              base_row=184.0, material_mode="clay", actor_key="front"):
        camera, record = frame_camera(
            scene, camera_record, world_y, angle=angle, width=width,
            base_row=base_row)
        actor = actors[actor_key]
        actor.hide_render = False
        actor.rotation_quaternion = camera.matrix_world.to_quaternion()
        if material_mode == "clay":
            override_objects(variants.get(active_key, source_group), clay)
        else:
            # Material studies only restore the generated objects by rerunning
            # the scratch process; source is intentionally not treated as a
            # generated material baseline.
            pass
        set_visible(variants.get(active_key, source_group), all_house_objects, actor)
        frame = render(scene, output, label)
        actor_pixels, actor_feet = measure_actor(scene, camera, world_y)
        frame.update({"active": active_key, "angleDegrees": angle,
                      "cameraTargetWidth": record["targetWidth"],
                      "actorPixels": actor_pixels, "actorFeetRow": actor_feet,
                      "mode": material_mode})
        frames.append(frame)

    # Consistent full-building front views: source, unchanged recipe, and two
    # explicit veranda controls. The second rhythm/depth proves composition.
    study("01_source_reference_front", "source", material_mode="clay")
    study("02_base_unchanged_front", "base", material_mode="materials")
    study("03_veranda_shallow_two_supports_front", "shallow")
    study("04_veranda_deep_four_supports_front", "deep")
    # A side-wall attachment and a side elevation make orientation visible.
    study("05_veranda_side_left_elevation", "side", angle=-90.0,
          actor_key="side")
    # Narrower authoring frame, lower baseline: a close junction/support study.
    study("06_veranda_deep_close_junction", "deep", width=256,
          base_row=208.0)

    report = {
        "seed": SEED,
        "source": source_report,
        "camera": {
            "fixture": "town_sideview_camera",
            "frontWidth": STUDY_WIDTH,
            "backX": BACK_X,
            "laneY": LANE_Y,
            "description": "consistent full-building authoring framing",
        },
        "actor": {"heightMetres": staging.WALKER_HEIGHT_M,
                  "expectedPixels": 48.0},
        "compositions": {
            "base": base.id,
            "shallow": shallow.as_json(),
            "deep": deep.as_json(),
            "side": side.as_json(),
        },
        "frames": frames,
        "limits": [
            "These are authoring studies, not Blender/runtime pixel parity.",
            "The material frame uses runtime vocabulary materials; source is not "
            "a generated replacement or a source bake.",
            "The side and close frames deliberately depart from the canon town "
            "view and are labelled as geometry studies.",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                        encoding="utf-8")
    print("HOUSE COMPARISON " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
