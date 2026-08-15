"""One-shot Blender scaffold for the character render lab.

The generated .blend files are editable source documents. This bootstrap is only
for initial materialization; once the sources are accepted, ordinary rendering
and export must treat them read-only.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as asset_core

ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = Path(os.environ.get(
    "SECOND_RITE_CHARACTER_LAB_SOURCE_DIR",
    ROOT / "assets" / "authoring" / "character_render_lab",
)).resolve()
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

FPS = 24
CLIPS = {
    "Idle": {"start": 1, "end": 24, "loop": True},
    "Walk": {"start": 1, "end": 16, "loop": True},
    "Talk": {"start": 1, "end": 20, "loop": True},
}


def _set_input(bsdf, names, value):
    for name in names:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def make_mat(name, color, *, roughness=0.55, metallic=0.0, coat=0.0, emission=None):
    mat = asset_core.make_material(
        name,
        color=color,
        roughness=roughness,
        metallic=metallic,
        emission=emission,
        scope="character_render_lab",
    )
    bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.use_nodes else None
    if bsdf is not None and coat:
        _set_input(bsdf, ("Coat Weight", "Clearcoat"), coat)
        _set_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), min(0.35, roughness))
    return mat


def smooth(obj, enabled=True):
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = bool(enabled)
    return obj


def add_ico(name, loc, scale, material, *, subdivisions=2, smooth_faces=True):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    smooth(obj, smooth_faces)
    asset_core.assign_material(obj, material)
    return obj


def add_uv(name, loc, scale, material, *, segments=20, rings=12, smooth_faces=True):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=1.0, location=loc
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    smooth(obj, smooth_faces)
    asset_core.assign_material(obj, material)
    return obj


def add_cone(name, loc, *, radius1, radius2, depth, material, vertices=12, smooth_faces=False):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
        end_fill_type="NGON",
        location=loc,
    )
    obj = bpy.context.object
    obj.name = name
    smooth(obj, smooth_faces)
    asset_core.assign_material(obj, material)
    return obj


def add_cube(name, loc, scale, material, *, bevel=0.0, smooth_faces=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    asset_core.assign_material(obj, material)
    if bevel:
        asset_core.add_bevel_modifier(obj, width=bevel, segments=2, angle_degrees=25.0)
    smooth(obj, smooth_faces)
    return obj


def add_wedge(name, loc, scale, material, *, mirror=False):
    sx, sy, sz = scale
    sign = -1.0 if mirror else 1.0
    verts = [
        (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
        (-0.75 * sx, -0.75 * sy, sz), (0.75 * sx, -0.75 * sy, sz),
        (sign * 0.35 * sx, 0.95 * sy, sz), (-sign * 0.95 * sx, 0.55 * sy, sz),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    asset_core.assign_material(obj, material)
    smooth(obj, False)
    return obj


def create_rig(character_id):
    arm_data = bpy.data.armatures.new(f"{character_id}_Armature")
    rig = bpy.data.objects.new(f"CHAR_{character_id}", arm_data)
    bpy.context.scene.collection.objects.link(rig)
    rig.show_in_front = True

    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, head, tail, parent=None):
        b = arm_data.edit_bones.new(name)
        b.head = head
        b.tail = tail
        if parent:
            b.parent = arm_data.edit_bones.get(parent)
        return b

    bone("root", (0, 0, 0.04), (0, 0, 0.18))
    bone("body", (0, 0, 0.48), (0, 0, 1.15), "root")
    bone("head", (0, 0, 1.12), (0, 0, 1.62), "body")
    bone("arm.L", (-0.26, 0, 1.03), (-0.54, 0, 0.76), "body")
    bone("arm.R", (0.26, 0, 1.03), (0.54, 0, 0.76), "body")
    bone("leg.L", (-0.14, 0, 0.55), (-0.16, 0, 0.14), "root")
    bone("leg.R", (0.14, 0, 0.55), (0.16, 0, 0.14), "root")
    bone("hair", (0, 0.10, 1.48), (0, 0.24, 1.20), "head")
    bone("accessory", (0, 0.09, 1.13), (0, 0.28, 0.78), "body")
    bpy.ops.object.mode_set(mode="POSE")
    for pbone in rig.pose.bones:
        pbone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")

    asset_core.tag_asset_target(
        rig,
        asset_id=character_id,
        representation="full_model",
        role="preview_only",
        authoring_space="preview",
        placement_frame="preview_frame",
        states=["default"],
        default_state="default",
        variants=[],
        extra={
            "sr_source_authority": "blend",
            "sr_character_render_lab": True,
            "sr_authored_forward": "-Y",
            "sr_rig_kind": "armature_rigid_parts",
            "sr_animation_clips_json": json.dumps(CLIPS, separators=(",", ":")),
            "sr_representation_intents_json": json.dumps(
                ["realtime_3d", "baked_sprite"], separators=(",", ":")
            ),
            "sr_final_raster_px": 24,
            "sr_render_supersample": 8,
        },
    )
    return rig


def bind(obj, rig, bone_name):
    # Rigid single-bone skin: disconnected authored parts remain legal while the
    # animation itself lives in one Armature action set.
    obj.parent = rig
    modifier = obj.modifiers.new("CharacterRig", "ARMATURE")
    modifier.object = rig
    group = obj.vertex_groups.new(name=bone_name)
    if obj.type == "MESH":
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    return obj


def reset_pose(rig):
    for pbone in rig.pose.bones:
        pbone.location = (0.0, 0.0, 0.0)
        pbone.rotation_euler = (0.0, 0.0, 0.0)
        pbone.scale = (1.0, 1.0, 1.0)


def key_pose(rig, frame):
    for name in ("root", "body", "head", "arm.L", "arm.R", "leg.L", "leg.R", "hair", "accessory"):
        pbone = rig.pose.bones[name]
        pbone.keyframe_insert("location", frame=frame, group=name)
        pbone.keyframe_insert("rotation_euler", frame=frame, group=name)
        pbone.keyframe_insert("scale", frame=frame, group=name)


def add_action(rig, name, frames, pose_fn):
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    rig.animation_data_create()
    # Blender 4.4+ Actions can be slotted. Create an explicit rig slot when
    # the API exposes it; older Blender versions simply ignore this branch.
    slot = None
    slots = getattr(action, "slots", None)
    if slots is not None and hasattr(slots, "new"):
        slot = slots.new(for_id=rig)
    rig.animation_data.action = action
    if slot is not None and hasattr(rig.animation_data, "action_slot"):
        rig.animation_data.action_slot = slot
    for frame in frames:
        reset_pose(rig)
        pose_fn(rig, frame)
        key_pose(rig, frame)
    for fcurve in getattr(action, "fcurves", []):
        for key in fcurve.keyframe_points:
            key.interpolation = "BEZIER"
    rig.animation_data.action = None
    return action


def build_actions(rig):
    idle_frames = (1, 7, 13, 19, 24)
    def idle_pose(r, frame):
        phase = (frame - 1) / 23.0 * math.tau
        r.pose.bones["root"].location.z = 0.018 * math.sin(phase)
        r.pose.bones["body"].rotation_euler.z = math.radians(1.8) * math.sin(phase)
        r.pose.bones["head"].rotation_euler.z = -math.radians(2.2) * math.sin(phase)
        r.pose.bones["hair"].rotation_euler.x = math.radians(3.0) * math.sin(phase - 0.5)
        r.pose.bones["accessory"].rotation_euler.x = math.radians(4.0) * math.sin(phase - 0.8)
    add_action(rig, "Idle", idle_frames, idle_pose)

    walk_frames = (1, 3, 5, 7, 9, 11, 13, 15, 16)
    def walk_pose(r, frame):
        phase = (frame - 1) / 15.0 * math.tau
        swing = math.sin(phase)
        lift = abs(math.sin(phase))
        r.pose.bones["root"].location.z = 0.045 * lift
        r.pose.bones["body"].rotation_euler.z = math.radians(3.0) * swing
        r.pose.bones["head"].rotation_euler.z = -math.radians(2.5) * swing
        r.pose.bones["leg.L"].rotation_euler.x = math.radians(31.0) * swing
        r.pose.bones["leg.R"].rotation_euler.x = -math.radians(31.0) * swing
        r.pose.bones["arm.L"].rotation_euler.x = -math.radians(24.0) * swing
        r.pose.bones["arm.R"].rotation_euler.x = math.radians(24.0) * swing
        r.pose.bones["hair"].rotation_euler.x = -math.radians(9.0) * swing
        r.pose.bones["accessory"].rotation_euler.x = -math.radians(12.0) * swing
    add_action(rig, "Walk", walk_frames, walk_pose)

    talk_frames = (1, 5, 9, 13, 17, 20)
    def talk_pose(r, frame):
        phase = (frame - 1) / 19.0 * math.tau
        pulse = 0.5 - 0.5 * math.cos(phase)
        r.pose.bones["root"].location.z = 0.012 * math.sin(phase * 2.0)
        r.pose.bones["body"].rotation_euler.z = math.radians(2.5) * math.sin(phase)
        r.pose.bones["head"].rotation_euler.x = math.radians(7.0) * math.sin(phase * 2.0)
        r.pose.bones["arm.R"].rotation_euler.x = math.radians(-42.0) * pulse
        r.pose.bones["arm.R"].rotation_euler.z = math.radians(-16.0) * pulse
        r.pose.bones["arm.L"].rotation_euler.x = math.radians(10.0) * math.sin(phase)
        r.pose.bones["hair"].rotation_euler.x = math.radians(4.0) * math.sin(phase - 0.4)
        r.pose.bones["accessory"].rotation_euler.x = math.radians(6.0) * math.sin(phase - 0.6)
    add_action(rig, "Talk", talk_frames, talk_pose)


def add_readme(character_id, approach):
    text = bpy.data.texts.new("CHARACTER_RENDER_LAB_README")
    text.write(
        f"Character render lab source: {character_id}\n\n"
        f"Approach: {approach}\n\n"
        "This .blend is an editable source document. The character is authored from disconnected rigid parts "
        "bound 100% to Armature bones; mesh continuity is not required.\n"
        "Actions: Idle, Walk, Talk. Facing is deliberately not duplicated per direction; runtime yaw or sprite "
        "bake direction resolves it.\n"
        "The lab contract is intentionally preview_only until a production character schema is proven.\n"
        "Final sprite target: exact 24x24 after 8x supersampled resolve; no vertex snapping.\n"
    )


def build_soft_doll():
    asset_core.reset_scene(factory=True)
    skin = make_mat("skin", (0.96, 0.69, 0.54), roughness=0.44)
    hair = make_mat("hair", (0.16, 0.055, 0.035), roughness=0.24, coat=0.12)
    teal = make_mat("teal_coat", (0.055, 0.30, 0.29), roughness=0.64)
    cream = make_mat("cream_trim", (0.88, 0.79, 0.62), roughness=0.56)
    boot = make_mat("boots", (0.07, 0.045, 0.04), roughness=0.42, coat=0.06)
    gold = make_mat("gold", (0.72, 0.48, 0.13), roughness=0.25, metallic=0.62, coat=0.12)
    eye = make_mat("eyes", (0.012, 0.016, 0.018), roughness=0.18, coat=0.25)

    rig = create_rig("character_lab_soft_doll")
    bind(add_uv("hair_back", (0, 0.055, 1.45), (0.43, 0.37, 0.43), hair, segments=24, rings=16), rig, "head")
    bind(add_uv("head", (0, -0.065, 1.43), (0.365, 0.335, 0.375), skin, segments=28, rings=18), rig, "head")
    bind(add_uv("hair_cap", (0, -0.015, 1.64), (0.38, 0.34, 0.22), hair, segments=20, rings=12), rig, "head")
    bind(add_cone("hair_lock_L", (-0.30, 0.01, 1.35), radius1=0.12, radius2=0.02, depth=0.42, material=hair, vertices=10, smooth_faces=True), rig, "hair")
    bind(add_cone("hair_lock_R", (0.30, 0.01, 1.34), radius1=0.12, radius2=0.02, depth=0.44, material=hair, vertices=10, smooth_faces=True), rig, "hair")
    # Eyes are tiny raised beads: shading can still separate them at 24px without billboard logic.
    bind(add_uv("eye_L", (-0.115, -0.373, 1.45), (0.035, 0.026, 0.050), eye, segments=12, rings=8), rig, "head")
    bind(add_uv("eye_R", (0.115, -0.373, 1.45), (0.035, 0.026, 0.050), eye, segments=12, rings=8), rig, "head")
    bind(add_uv("nose", (0, -0.405, 1.37), (0.028, 0.022, 0.032), skin, segments=10, rings=6), rig, "head")

    bind(add_cone("coat", (0, 0, 0.82), radius1=0.31, radius2=0.245, depth=0.66, material=teal, vertices=16, smooth_faces=True), rig, "body")
    bind(add_cone("collar", (0, -0.01, 1.12), radius1=0.27, radius2=0.20, depth=0.12, material=cream, vertices=16, smooth_faces=True), rig, "body")
    bind(add_cube("belt", (0, -0.015, 0.72), (0.30, 0.17, 0.045), gold, bevel=0.03), rig, "body")

    for side, x, bone in (("L", -0.39, "arm.L"), ("R", 0.39, "arm.R")):
        bind(add_uv(f"sleeve_{side}", (x, 0, 0.88), (0.16, 0.15, 0.28), teal, segments=16, rings=10), rig, bone)
        bind(add_uv(f"hand_{side}", (x * 1.10, -0.015, 0.67), (0.125, 0.12, 0.12), skin, segments=16, rings=10), rig, bone)
    for side, x, bone in (("L", -0.15, "leg.L"), ("R", 0.15, "leg.R")):
        bind(add_uv(f"leg_{side}", (x, 0.02, 0.39), (0.13, 0.14, 0.23), cream, segments=14, rings=9), rig, bone)
        shoe = add_uv(f"boot_{side}", (x, -0.09, 0.15), (0.16, 0.24, 0.12), boot, segments=16, rings=10)
        shoe.rotation_euler.x = math.radians(-7)
        bind(shoe, rig, bone)

    scarf = add_cone("scarf_tail", (0.10, 0.18, 0.91), radius1=0.095, radius2=0.025, depth=0.50, material=cream, vertices=10, smooth_faces=True)
    scarf.rotation_euler.x = math.radians(-18)
    bind(scarf, rig, "accessory")
    build_actions(rig)
    add_readme("character_lab_soft_doll", "A — soft pre-rendered doll: smooth volumes, glossy hair, cloth/skin material separation")
    return rig


def build_faceted_courier():
    asset_core.reset_scene(factory=True)
    skin = make_mat("skin", (0.78, 0.48, 0.34), roughness=0.58)
    hair = make_mat("hair", (0.025, 0.035, 0.050), roughness=0.34, coat=0.08)
    coat = make_mat("vermilion_coat", (0.47, 0.065, 0.045), roughness=0.66)
    cyan = make_mat("cyan_sash", (0.05, 0.53, 0.60), roughness=0.42, coat=0.08)
    leather = make_mat("satchel", (0.25, 0.105, 0.045), roughness=0.52)
    boot = make_mat("boots", (0.045, 0.055, 0.06), roughness=0.36, coat=0.12)
    eye = make_mat("eyes", (0.01, 0.012, 0.015), roughness=0.24)

    rig = create_rig("character_lab_faceted_courier")
    bind(add_ico("head", (0, -0.035, 1.43), (0.36, 0.33, 0.38), skin, subdivisions=2, smooth_faces=False), rig, "head")
    bind(add_wedge("hair_mass", (0, 0.045, 1.62), (0.39, 0.34, 0.23), hair), rig, "head")
    bang = add_wedge("hair_bang", (-0.11, -0.30, 1.58), (0.22, 0.10, 0.16), hair, mirror=True)
    bang.rotation_euler.x = math.radians(8)
    bind(bang, rig, "hair")
    bind(add_ico("eye_L", (-0.12, -0.335, 1.44), (0.042, 0.025, 0.045), eye, subdivisions=1, smooth_faces=False), rig, "head")
    bind(add_ico("eye_R", (0.12, -0.335, 1.44), (0.042, 0.025, 0.045), eye, subdivisions=1, smooth_faces=False), rig, "head")

    bind(add_cone("coat", (0, 0.0, 0.82), radius1=0.34, radius2=0.23, depth=0.70, material=coat, vertices=7), rig, "body")
    sash = add_cube("sash", (0.0, -0.18, 0.91), (0.29, 0.045, 0.055), cyan, bevel=0.018)
    sash.rotation_euler.z = math.radians(-13)
    bind(sash, rig, "body")
    satchel = add_cube("satchel", (0.38, 0.08, 0.72), (0.16, 0.12, 0.18), leather, bevel=0.04)
    satchel.rotation_euler.z = math.radians(-8)
    bind(satchel, rig, "accessory")

    for side, x, bone, mir in (("L", -0.41, "arm.L", False), ("R", 0.41, "arm.R", True)):
        sleeve = add_wedge(f"sleeve_{side}", (x, 0.0, 0.87), (0.15, 0.14, 0.27), coat, mirror=mir)
        bind(sleeve, rig, bone)
        bind(add_ico(f"hand_{side}", (x * 1.08, -0.025, 0.66), (0.115, 0.105, 0.115), skin, subdivisions=1, smooth_faces=False), rig, bone)
    for side, x, bone in (("L", -0.16, "leg.L"), ("R", 0.16, "leg.R")):
        bind(add_cone(f"leg_{side}", (x, 0.02, 0.39), radius1=0.13, radius2=0.10, depth=0.38, material=cyan, vertices=7), rig, bone)
        shoe = add_wedge(f"boot_{side}", (x, -0.105, 0.14), (0.16, 0.24, 0.11), boot, mirror=(side == "R"))
        bind(shoe, rig, bone)

    ribbon = add_wedge("sash_tail", (-0.17, 0.19, 0.72), (0.11, 0.055, 0.31), cyan, mirror=True)
    ribbon.rotation_euler.x = math.radians(-10)
    bind(ribbon, rig, "accessory")
    build_actions(rig)
    add_readme("character_lab_faceted_courier", "B — faceted couture: directional planes, asymmetry and hard light-catching geometry")
    return rig


def build_shrine_mage():
    asset_core.reset_scene(factory=True)
    skin = make_mat("skin", (0.86, 0.57, 0.44), roughness=0.48)
    hair = make_mat("hair", (0.10, 0.045, 0.15), roughness=0.30, coat=0.10)
    ivory = make_mat("ivory_robe", (0.83, 0.76, 0.62), roughness=0.72)
    indigo = make_mat("indigo", (0.075, 0.10, 0.28), roughness=0.48)
    gold = make_mat("gold", (0.82, 0.55, 0.14), roughness=0.22, metallic=0.72, coat=0.12)
    gem = make_mat("gem", (0.07, 0.46, 0.50), roughness=0.16, metallic=0.05, coat=0.25, emission=(0.015, 0.10, 0.11))
    eye = make_mat("eyes", (0.014, 0.012, 0.025), roughness=0.18)

    rig = create_rig("character_lab_shrine_mage")
    bind(add_uv("hair_back", (0, 0.075, 1.43), (0.44, 0.36, 0.47), hair, segments=24, rings=16), rig, "head")
    bind(add_uv("head", (0, -0.075, 1.45), (0.34, 0.31, 0.36), skin, segments=24, rings=14), rig, "head")
    bind(add_uv("hair_crown", (0, 0.0, 1.68), (0.36, 0.31, 0.20), hair, segments=18, rings=10), rig, "head")
    bind(add_uv("eye_L", (-0.11, -0.365, 1.46), (0.034, 0.022, 0.045), eye, segments=10, rings=6), rig, "head")
    bind(add_uv("eye_R", (0.11, -0.365, 1.46), (0.034, 0.022, 0.045), eye, segments=10, rings=6), rig, "head")
    jewel = add_ico("forehead_gem", (0, -0.365, 1.64), (0.055, 0.028, 0.065), gem, subdivisions=1, smooth_faces=False)
    jewel.rotation_euler.y = math.radians(45)
    bind(jewel, rig, "head")

    bind(add_cone("robe", (0, 0.03, 0.69), radius1=0.44, radius2=0.22, depth=0.95, material=ivory, vertices=14, smooth_faces=True), rig, "body")
    bind(add_cone("upper_robe", (0, -0.005, 1.02), radius1=0.27, radius2=0.24, depth=0.42, material=indigo, vertices=14, smooth_faces=True), rig, "body")
    bind(add_cone("gold_collar", (0, -0.005, 1.19), radius1=0.265, radius2=0.19, depth=0.10, material=gold, vertices=14, smooth_faces=True), rig, "body")
    bind(add_cube("gold_belt", (0, -0.02, 0.72), (0.32, 0.17, 0.035), gold, bevel=0.025), rig, "body")

    for side, x, bone in (("L", -0.43, "arm.L"), ("R", 0.43, "arm.R")):
        bind(add_uv(f"sleeve_{side}", (x, 0.01, 0.91), (0.20, 0.18, 0.30), ivory, segments=18, rings=10), rig, bone)
        bind(add_uv(f"hand_{side}", (x * 1.08, -0.035, 0.68), (0.11, 0.10, 0.105), skin, segments=14, rings=8), rig, bone)
    # Feet are almost hidden by the robe, but remain large dark anchors when the walk opens the silhouette.
    for side, x, bone in (("L", -0.15, "leg.L"), ("R", 0.15, "leg.R")):
        bind(add_uv(f"foot_{side}", (x, -0.08, 0.13), (0.16, 0.22, 0.10), indigo, segments=14, rings=8), rig, bone)

    pony = add_cone("ponytail", (0.18, 0.18, 1.27), radius1=0.15, radius2=0.035, depth=0.68, material=hair, vertices=12, smooth_faces=True)
    pony.rotation_euler.x = math.radians(-16)
    pony.rotation_euler.z = math.radians(-12)
    bind(pony, rig, "hair")
    tassel = add_cone("gold_tassel", (-0.16, 0.16, 0.78), radius1=0.08, radius2=0.025, depth=0.48, material=gold, vertices=10, smooth_faces=True)
    tassel.rotation_euler.x = math.radians(-15)
    bind(tassel, rig, "accessory")
    build_actions(rig)
    add_readme("character_lab_shrine_mage", "C — ornamental sprite sculpt: broad robe silhouette, material accents and animated secondary masses")
    return rig


BUILDERS = {
    "character_lab_soft_doll": build_soft_doll,
    "character_lab_faceted_courier": build_faceted_courier,
    "character_lab_shrine_mage": build_shrine_mage,
}


def save_source(character_id, rig):
    rig["sr_source_authority"] = "blend"
    path = SOURCE_DIR / f"{character_id}.blend"
    bpy.context.scene.render.fps = FPS
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    print(f"CHARACTER_LAB_SOURCE {character_id} {path}")
    return path


def main():
    only = os.environ.get("SECOND_RITE_CHARACTER_LAB_ONLY")
    ids = [only] if only else list(BUILDERS)
    for character_id in ids:
        if character_id not in BUILDERS:
            raise SystemExit(f"unknown character lab id: {character_id}")
        destination = SOURCE_DIR / f"{character_id}.blend"
        if destination.exists() and os.environ.get("SECOND_RITE_CHARACTER_LAB_OVERWRITE") != "1":
            raise SystemExit(
                f"refusing to overwrite existing source authority: {destination}; "
                "set SECOND_RITE_CHARACTER_LAB_OVERWRITE=1 only during disposable lab iteration"
            )
        rig = BUILDERS[character_id]()
        save_source(character_id, rig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
