"""Read-only realtime export + oversampled sprite renderer for the character lab.

Run from Blender with an existing source document open, for example:

  blender --background assets/authoring/character_render_lab/foo.blend \
    --python tools/blender/render_character_render_lab.py -- --out /tmp/foo

The source .blend is never saved. A SHA-256 before/after assertion is part of the
renderer because the lab is explicitly testing one Blender source feeding two
representations: realtime GLB and baked 24px sprites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as asset_core

FINAL_PX = 24
SUPERSAMPLE = 8
INTERNAL_PX = FINAL_PX * SUPERSAMPLE
DIRECTIONS = {
    "south": 0.0,
    "east": 90.0,
    "north": 180.0,
    "west": -90.0,
}
SAMPLES = {
    "Idle": [1, 7, 13, 19],
    "Walk": [1, 4, 7, 10, 13, 16],
    "Talk": [1, 5, 9, 13, 17, 20],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_rig():
    candidates = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE" and bool(obj.get("sr_character_render_lab", False))
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one character-lab Armature, found {len(candidates)}")
    rig = candidates[0]
    asset_core.validate_asset_metadata(rig)
    if rig.get("sr_source_authority") != "blend":
        raise RuntimeError("character lab source is not marked sr_source_authority=blend")
    return rig


def enum_identifiers(target, property_name):
    try:
        prop = target.bl_rna.properties[property_name]
        return {item.identifier for item in prop.enum_items}
    except Exception:
        return set()


def choose_enum(target, property_name, candidates):
    values = enum_identifiers(target, property_name)
    for value in candidates:
        if value in values:
            setattr(target, property_name, value)
            return value
    return getattr(target, property_name, None)


def set_socket(node, names, value):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def render_material(name, color, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        set_socket(bsdf, ("Base Color",), (*color, alpha))
        set_socket(bsdf, ("Roughness",), 1.0)
        set_socket(bsdf, ("Metallic",), 0.0)
        set_socket(bsdf, ("Alpha",), alpha)
    material.diffuse_color = (*color, alpha)
    if alpha < 1.0:
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        elif hasattr(material, "blend_method"):
            material.blend_method = "BLEND"
    return material


def add_contact_blob():
    # Render-only footprint anchor. It is deliberately not parented to the rig,
    # and is deleted implicitly when Blender exits without saving the source.
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32, ring_count=12, radius=1.0, location=(0.0, 0.04, 0.025)
    )
    blob = bpy.context.object
    blob.name = "RENDER_ONLY_contact_blob"
    blob.scale = (0.46, 0.30, 0.024)
    blob.data.materials.append(render_material("RENDER_ONLY_shadow", (0.015, 0.012, 0.022), 0.27))
    for poly in blob.data.polygons:
        poly.use_smooth = True
    blob["sr_render_only"] = True
    return blob


def point_camera(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera():
    data = bpy.data.cameras.new("CharacterLabCamera")
    camera = bpy.data.objects.new("CharacterLabCamera", data)
    bpy.context.scene.collection.objects.link(camera)
    # A weak 3/4-top orthographic view: enough crown/shoulder information to
    # read like a polished pre-render rather than a flat side elevation.
    camera.location = (0.0, -5.8, 3.25)
    point_camera(camera, (0.0, 0.0, 0.92))
    data.type = "ORTHO"
    data.ortho_scale = 2.22
    data.lens = 58.0
    bpy.context.scene.camera = camera
    return camera


def add_area(name, location, color, energy, size, target=(0.0, 0.0, 0.90)):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK" if "DISK" in enum_identifiers(data, "shape") else data.shape
    data.size = size
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    point_camera(light, target)
    return light


def configure_scene():
    scene = bpy.context.scene
    engine_values = enum_identifiers(scene.render, "engine")
    if "BLENDER_EEVEE_NEXT" in engine_values:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engine_values:
        scene.render.engine = "BLENDER_EEVEE"

    scene.render.resolution_x = INTERNAL_PX
    scene.render.resolution_y = INTERNAL_PX
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True

    # Stable subpixel rendering: the deliberate raster constraint is the final
    # 24px resolve, not PS1 vertex quantisation or object-space snapping.
    scene.render.use_motion_blur = False
    if hasattr(scene.render, "film_transparent_glass"):
        scene.render.film_transparent_glass = True

    view = scene.view_settings
    choose_enum(view, "view_transform", ("AgX", "Standard"))
    choose_enum(view, "look", (
        "AgX - Medium High Contrast", "Medium High Contrast",
        "AgX - Medium High Contrast Look", "None",
    ))
    view.exposure = 0.35

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.018, 0.022, 0.040, 1.0)
        background.inputs["Strength"].default_value = 0.18

    camera = add_camera()
    # Intentionally theatrical: warm frontal key gives readable face/torso
    # modelling; cool back rim separates tiny limbs/hair; soft top fill keeps
    # the shadow side from collapsing into one 24px blob.
    add_area("KEY_warm", (-3.4, -4.6, 6.2), (1.0, 0.58, 0.36), 760.0, 3.2)
    add_area("RIM_cool", (3.8, 2.8, 4.7), (0.24, 0.50, 1.0), 900.0, 2.5)
    add_area("FILL_top", (0.4, -0.3, 6.6), (0.70, 0.82, 1.0), 410.0, 4.5)
    add_contact_blob()
    return camera


def action_by_name(name):
    action = bpy.data.actions.get(name)
    if action is None:
        raise RuntimeError(f"source is missing Action {name!r}")
    return action


def assign_action(rig, action):
    animation = rig.animation_data_create()
    animation.action = action
    # Explicit slot assignment is only necessary/available on Blender's slotted
    # Action API. Prefer a compatible slot already stored in the action.
    if hasattr(animation, "action_slot"):
        slots = list(getattr(action, "slots", []))
        if slots:
            try:
                animation.action_slot = slots[0]
            except Exception:
                pass


def render_frame(rig, action_name, direction, frame, destination):
    action = action_by_name(action_name)
    assign_action(rig, action)
    rig.rotation_euler.z = math.radians(DIRECTIONS[direction])
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(destination)
    result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"render failed for {action_name}/{direction}/{frame}: {result}")
    if not destination.is_file():
        # PNG extension behavior is version/configuration-dependent.
        with_png = destination.with_suffix(".png")
        if with_png.is_file():
            return with_png
        raise RuntimeError(f"render did not create {destination}")
    return destination


def _operator_kwargs(operator, candidates):
    rna = operator.get_rna_type()
    supported = {prop.identifier: prop for prop in rna.properties}
    output = {}
    for name, value in candidates.items():
        prop = supported.get(name)
        if prop is None:
            continue
        if getattr(prop, "type", None) == "ENUM":
            choices = {item.identifier for item in prop.enum_items}
            if value not in choices:
                continue
        output[name] = value
    return output


def select_character(rig):
    bpy.ops.object.select_all(action="DESELECT")
    selected = [rig]
    selected.extend(obj for obj in rig.children_recursive if obj.type in {"MESH", "EMPTY"})
    for obj in selected:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    return selected


def export_glb(rig, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    rig.rotation_euler.z = 0.0
    assign_action(rig, action_by_name("Idle"))
    bpy.context.scene.frame_set(1)
    select_character(rig)
    operator = bpy.ops.export_scene.gltf
    candidates = {
        "filepath": str(destination),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_animation_mode": "ACTIONS",
        "export_force_sampling": True,
        "export_skins": True,
        "export_morph": False,
        "export_yup": True,
        "export_apply": False,
        "export_materials": "EXPORT",
        "export_cameras": False,
        "export_lights": False,
        "export_extras": True,
    }
    kwargs = _operator_kwargs(operator, candidates)
    result = operator(**kwargs)
    if "FINISHED" not in result or not destination.is_file():
        raise RuntimeError(f"glTF export failed: {result}; kwargs={sorted(kwargs)}")
    return {
        "path": str(destination),
        "bytes": destination.stat().st_size,
        "operatorArgs": sorted(kwargs),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--skip-glb", action="store_true")
    args = parser.parse_args(argv)

    source = Path(bpy.data.filepath).resolve()
    if not source.is_file():
        raise SystemExit("character renderer requires an already-saved .blend source")
    before = sha256(source)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    rig = find_rig()
    character_id = rig.get("sr_asset_id")
    configure_scene()

    glb_record = None
    if not args.skip_glb:
        glb_record = export_glb(rig, out / "realtime" / f"{character_id}.glb")

    rendered = []
    for action_name, frames in SAMPLES.items():
        for direction in DIRECTIONS:
            for frame in frames:
                path = out / "raw" / character_id / action_name.lower() / direction / f"{frame:03d}.png"
                actual = render_frame(rig, action_name, direction, frame, path)
                rendered.append(str(actual.relative_to(out)))

    after = sha256(source)
    if before != after:
        raise RuntimeError("read-only character rendering mutated the source .blend")

    manifest = {
        "schema": "thestra.character-render-lab/v0",
        "characterId": character_id,
        "source": str(source),
        "sourceBytes": source.stat().st_size,
        "sourceSha256": before,
        "sourceUnchanged": True,
        "finalRaster": [FINAL_PX, FINAL_PX],
        "internalRaster": [INTERNAL_PX, INTERNAL_PX],
        "supersample": SUPERSAMPLE,
        "vertexSnapping": False,
        "camera": {
            "projection": "orthographic",
            "position": [0.0, -5.8, 3.25],
            "target": [0.0, 0.0, 0.92],
            "orthoScale": 2.22,
        },
        "directionsDegrees": DIRECTIONS,
        "samples": SAMPLES,
        "actionsInBlend": sorted(action.name for action in bpy.data.actions),
        "realtime": glb_record,
        "rawFrames": rendered,
        "blenderVersion": bpy.app.version_string,
    }
    manifest_path = out / f"{character_id}.render-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("CHARACTER_LAB_RENDER " + json.dumps(manifest, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    raise SystemExit(main(script_args))
