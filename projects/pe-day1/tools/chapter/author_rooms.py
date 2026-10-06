"""Author the PE Day 1 interiors (lobby .. rehearsal room) as Second Gate
environment sources: one .blend per room in the TH_* contract that
tools/blender/town_environment_pipeline.py bakes into a lit atlas package.

    python tools/blender/run.py projects/pe-day1/tools/chapter/author_rooms.py -- --room foyer

Room size and door placement come from rooms.json, so the baked art and the
playable bounds cannot drift apart. This script makes the FIRST version of a
room's .blend; once a room is adopted its .blend is the authority -- edit it in
Blender and re-bake, don't re-run this over it (it refuses to overwrite).

Look targets, read from the private reference pack (never shipped):
low-key interiors lit by a few warm practical lights, nothing lit by the
"sky"; patterned dark floors, red carpet and brass in the lobby; a black stage
with a pale staircase; cream-framed red doors backstage; warm bulb-lit
vanities; a plank-floored rehearsal room with a black grand piano.
All geometry and materials here are original.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
OUT = PROJECT / "assets" / "authoring" / "environments"
ROOMS = json.loads((HERE / "rooms.json").read_text(encoding="utf-8"))
WALL_H = 3.4
FRONT = 3.0


# --- scene + collections ------------------------------------------------------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    world = bpy.data.worlds.new("pe_black")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    scene.world = world
    cols = {}
    for name in ("TH_SOURCE", "TH_RENDER", "TH_ANCHORS", "TH_CAMERA_PREVIEW"):
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        cols[name] = c
    return cols


def link(obj, col):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


# --- materials ------------------------------------------------------------------

def mat(name, color, rough=0.7, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def patterned(name, a, b, kind, scale, rough=0.6):
    """Procedural albedo: checker (diamond tiles), wave (planks), brick, noise."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    if kind == "diamond":
        mapping.inputs["Rotation"].default_value = (0, 0, math.radians(45))
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    if kind in ("checker", "diamond"):
        tex = nt.nodes.new("ShaderNodeTexChecker")
        tex.inputs["Color1"].default_value = (*a, 1)
        tex.inputs["Color2"].default_value = (*b, 1)
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    elif kind == "brick":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        tex.inputs["Color1"].default_value = (*a, 1)
        tex.inputs["Color2"].default_value = (*[c * 0.85 for c in a], 1)
        tex.inputs["Mortar"].default_value = (*b, 1)
        tex.inputs["Mortar Size"].default_value = 0.015
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    else:  # planks / wallpaper stripes / noise
        tex = nt.nodes.new("ShaderNodeTexWave" if kind in ("planks", "stripes") else "ShaderNodeTexNoise")
        if kind in ("planks", "stripes"):
            tex.wave_type = "BANDS"
            tex.bands_direction = "X"
            tex.inputs["Distortion"].default_value = 2.0 if kind == "planks" else 0.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*a, 1)
        ramp.color_ramp.elements[1].color = (*b, 1)
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


# --- geometry helpers -------------------------------------------------------------

def box(col, name, center, size, material, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=(0, 0, rot_z))
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    return link(o, col)


def cyl(col, name, center, radius, depth, material, verts=12, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=center, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    return link(o, col)


def sphere(col, name, center, radius, material, segs=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(4, segs // 2), radius=radius, location=center)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    return link(o, col)


def light(col, name, kind, loc, energy, color, size=0.3, rot=(0, 0, 0), spot=None):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind in ("POINT", "SPOT"):
        data.shadow_soft_size = size
    if kind == "AREA":
        data.size = size
    if kind == "SPOT" and spot:
        data.spot_size = math.radians(spot)
        data.spot_blend = 0.45
    o = bpy.data.objects.new(name, data)
    o.location = loc
    o.rotation_euler = rot
    col.objects.link(o)
    return o


def door_point(room, door):
    w, d = room["size"]
    return {"back": (door["at"], d), "front": (door["at"], 0.0),
            "left": (-w / 2, door["at"]), "right": (w / 2, door["at"])}[door["wall"]]


# --- shared shell -------------------------------------------------------------------

def shell(S, room, floor_m, wall_m, base_m, door_m, frame_m):
    w, d = room["size"]
    # Floor and side walls run FRONT metres toward the camera, so a close,
    # low camera never sees past the room's edge into the void.
    f = FRONT
    box(S, "floor", (0, (d - f) / 2, -0.05), (w + 0.6, d + f + 0.6, 0.1), floor_m)
    box(S, "wall_back", (0, d + 0.15, WALL_H / 2), (w + 0.6, 0.3, WALL_H), wall_m)
    box(S, "wall_left", (-w / 2 - 0.15, (d - f) / 2, WALL_H / 2), (0.3, d + f + 0.6, WALL_H), wall_m)
    box(S, "wall_right", (w / 2 + 0.15, (d - f) / 2, WALL_H / 2), (0.3, d + f + 0.6, WALL_H), wall_m)
    for name, c, s in (("base_back", (0, d - 0.02, 0.09), (w, 0.06, 0.18)),
                       ("base_left", (-w / 2 + 0.02, d / 2, 0.09), (0.06, d, 0.18)),
                       ("base_right", (w / 2 - 0.02, d / 2, 0.09), (0.06, d, 0.18))):
        box(S, name, c, s, base_m)
    for door in room["doors"]:
        x, y = door_point(room, door)
        if door["wall"] == "front":
            continue
        double = door.get("needs") is None and door["wall"] == "back"
        width = 1.5 if double else 1.0
        if door["wall"] == "back":
            box(S, "door_" + door["id"], (x, y - 0.02, 1.1), (width, 0.06, 2.2), door_m)
            box(S, "frame_" + door["id"], (x, y - 0.0, 1.2), (width + 0.3, 0.05, 2.4), frame_m)
            box(S, "bar_" + door["id"], (x + width * 0.3, y - 0.07, 1.05), (0.05, 0.04, 0.5), frame_m)
        else:
            sx = -1 if door["wall"] == "left" else 1
            box(S, "door_" + door["id"], (x - sx * 0.02, y, 1.1), (0.06, width, 2.2), door_m)
            box(S, "frame_" + door["id"], (x, y, 1.2), (0.05, width + 0.3, 2.4), frame_m)
            box(S, "bar_" + door["id"], (x - sx * 0.07, y - width * 0.3, 1.05), (0.04, 0.05, 0.5), frame_m)


# --- rooms ------------------------------------------------------------------------

WARM = (1.0, 0.72, 0.42)
BRASS = None


def chandelier(S, name, x, y, z, scale=1.0):
    gold = mat("brass", (0.75, 0.55, 0.22), 0.35, 1.0)
    crystal = mat("crystal_glow", (1.0, 0.9, 0.7), 0.2, emit=(1.0, 0.82, 0.55), strength=6.0)
    cyl(S, name + "_stem", (x, y, z + 0.5 * scale), 0.03, 1.0 * scale, gold, 6)
    for tier, (r, h) in enumerate(((0.55, 0.0), (0.38, 0.28), (0.2, 0.5))):
        cyl(S, "%s_ring%d" % (name, tier), (x, y, z + h * scale), r * scale, 0.05, gold, 16)
        for i in range(8 - tier * 2):
            a = i / (8 - tier * 2) * math.tau
            sphere(S, "%s_drop%d_%d" % (name, tier, i), (x + math.cos(a) * r * scale, y + math.sin(a) * r * scale,
                                                         z + h * scale - 0.1), 0.06 * scale, crystal, 6)
    light(S, name + "_light", "POINT", (x, y, z - 0.2), 260 * scale, WARM, 0.5)


def room_foyer(S, room):
    w, d = room["size"]
    floor = patterned("lobby_tiles", (0.16, 0.06, 0.04), (0.33, 0.17, 0.08), "diamond", 1.6, 0.45)
    wall = patterned("lobby_panels", (0.30, 0.17, 0.09), (0.20, 0.10, 0.05), "stripes", 1.2, 0.6)
    shell(S, room, floor, wall, mat("dark_wood", (0.12, 0.05, 0.03), 0.5),
          mat("door_red", (0.42, 0.03, 0.03), 0.5), mat("brass", (0.75, 0.55, 0.22), 0.35, 1.0))
    red = mat("carpet_red", (0.22, 0.01, 0.015), 0.9)
    box(S, "runner", (0, d / 2, 0.012), (1.8, d, 0.025), red)
    gold = mat("brass", (0.75, 0.55, 0.22), 0.35, 1.0)
    rope = mat("rope_red", (0.5, 0.03, 0.04), 0.8)
    for side in (-1, 1):
        posts = [0.8 + i * 1.3 for i in range(int((d - 1.2) / 1.3) + 1)]
        for i, py in enumerate(posts):
            cyl(S, "post_%d_%d" % (side, i), (side * 1.25, py, 0.45), 0.05, 0.9, gold, 10)
            sphere(S, "knob_%d_%d" % (side, i), (side * 1.25, py, 0.92), 0.07, gold, 8)
            cyl(S, "foot_%d_%d" % (side, i), (side * 1.25, py, 0.02), 0.16, 0.04, gold, 12)
            if i + 1 < len(posts):
                cyl(S, "rope_%d_%d" % (side, i), (side * 1.25, (py + posts[i + 1]) / 2, 0.78), 0.025, 1.25, rope, 6,
                    rot=(math.radians(90), 0, 0))
    col = mat("marble_col", (0.55, 0.47, 0.36), 0.35)
    for sx in (-1, 1):
        for py in (1.2, d - 1.2):
            cyl(S, "column_%d_%.0f" % (sx, py), (sx * (w / 2 - 0.5), py, WALL_H / 2), 0.28, WALL_H, col, 16)
    chandelier(S, "chand_a", 0, d * 0.3, 2.9)
    chandelier(S, "chand_b", 0, d * 0.75, 2.9)
    for sx in (-1, 1):
        light(S, "sconce_%d" % sx, "POINT", (sx * (w / 2 - 0.3), d * 0.5, 2.0), 60, WARM, 0.2)


def room_auditorium(S, room):
    w, d = room["size"]
    floor = mat("hall_carpet", (0.22, 0.03, 0.04), 0.95)
    wall = patterned("hall_panels", (0.24, 0.12, 0.06), (0.14, 0.06, 0.03), "stripes", 1.0)
    shell(S, room, floor, wall, mat("dark_wood", (0.12, 0.05, 0.03), 0.5),
          mat("door_red", (0.42, 0.03, 0.03), 0.5), mat("brass", (0.75, 0.55, 0.22), 0.35, 1.0))
    seat = mat("seat_velvet", (0.45, 0.04, 0.05), 0.9)
    wood = mat("dark_wood", (0.12, 0.05, 0.03), 0.5)
    stage_d = 2.0
    box(S, "stage_apron", (0, d - stage_d / 2, 0.45), (w, stage_d, 0.9), mat("stage_boards", (0.22, 0.13, 0.07), 0.6))
    curtain = patterned("curtain", (0.40, 0.02, 0.03), (0.22, 0.01, 0.02), "stripes", 5.0, 0.95)
    for sx in (-1, 1):
        box(S, "curtain_%d" % sx, (sx * (w / 2 - 1.2), d - 0.2, 2.1), (2.4, 0.2, 2.6), curtain)
    box(S, "valance", (0, d - 0.25, 3.15), (w, 0.25, 0.5), curtain)
    rows = int((d - stage_d - 1.4) / 0.9)
    for r in range(rows):
        y = 0.9 + r * 0.9
        for sx in (-1, 1):
            for c in range(4):
                x = sx * (1.1 + c * 0.75)
                box(S, "seat_%d_%d_%d" % (r, sx, c), (x, y, 0.25), (0.6, 0.5, 0.12), seat)
                box(S, "back_%d_%d_%d" % (r, sx, c), (x, y - 0.25, 0.5), (0.6, 0.08, 0.6), seat)
                box(S, "frame_%d_%d_%d" % (r, sx, c), (x, y, 0.1), (0.62, 0.5, 0.2), wood)
    light(S, "stage_wash", "SPOT", (0, d - 4.5, 4.5), 900, (1.0, 0.75, 0.5), 0.4,
          rot=(math.radians(45), 0, 0), spot=55)
    for sx in (-1, 1):
        light(S, "aisle_%d" % sx, "POINT", (sx * (w / 2 - 0.4), d * 0.4, 2.2), 45, WARM, 0.2)
    chandelier(S, "chand", 0, d * 0.35, 3.0, 0.8)


def room_stage(S, room):
    w, d = room["size"]
    boards = patterned("stage_planks", (0.10, 0.06, 0.035), (0.20, 0.12, 0.07), "planks", 2.5, 0.55)
    black = mat("stage_black", (0.02, 0.02, 0.025), 0.9)
    shell(S, room, boards, black, black, mat("door_dark", (0.12, 0.10, 0.10), 0.5),
          mat("frame_grey", (0.4, 0.38, 0.35), 0.5))
    stone = mat("stair_stone", (0.62, 0.60, 0.56), 0.5)
    for i in range(9):  # the pale stage staircase rising to the back-right
        box(S, "step_%d" % i, (w / 2 - 1.6, d - 0.9 - i * 0.0, 0.11 + i * 0.22), (2.2, 1.6 - i * 0.12, 0.22), stone)
    for i in range(9):
        cyl(S, "baluster_%d" % i, (w / 2 - 2.75, d - 1.6 + i * 0.12, 0.25 + i * 0.22 + 0.35), 0.03, 0.7, stone, 6)
    box(S, "handrail", (w / 2 - 2.75, d - 1.1, 1.3), (0.06, 1.3, 0.06), stone, 0)
    curtain = patterned("curtain", (0.40, 0.02, 0.03), (0.22, 0.01, 0.02), "stripes", 5.0, 0.95)
    box(S, "backdrop", (-1.5, d - 0.05, 1.7), (w - 4, 0.1, 3.4), curtain)
    light(S, "spot_main", "SPOT", (0.0, 1.0, 5.0), 1400, (1.0, 0.85, 0.65), 0.3,
          rot=(math.radians(25), 0, 0), spot=40)
    light(S, "stair_glow", "SPOT", (w / 2 - 1.6, d - 3.5, 4.5), 120, (0.85, 0.85, 1.0), 0.3,
          rot=(math.radians(35), 0, 0), spot=35)
    for i in range(7):  # embers left by the fire
        sphere(S, "ember_%d" % i, (-2.5 + i * 0.8, 1.5 + (i % 3) * 0.6, 0.02), 0.03,
               mat("ember", (1, 0.3, 0.05), 0.5, emit=(1, 0.35, 0.05), strength=8), 6)


def room_backstage(S, room):
    w, d = room["size"]
    floor = patterned("concrete", (0.18, 0.17, 0.15), (0.26, 0.25, 0.22), "noise", 3.0, 0.8)
    wall = patterned("masonry", (0.30, 0.26, 0.20), (0.14, 0.12, 0.10), "brick", 1.4, 0.85)
    shell(S, room, floor, wall, mat("dark_base", (0.08, 0.07, 0.06), 0.6),
          mat("door_red", (0.42, 0.03, 0.03), 0.5), mat("frame_cream", (0.72, 0.66, 0.52), 0.5))
    lamp = mat("lamp_glow", (1, 0.9, 0.7), 0.3, emit=(1, 0.85, 0.6), strength=10)
    for i, y in enumerate((d * 0.25, d * 0.7)):
        box(S, "lamp_%d" % i, (0, y, WALL_H - 0.05), (0.5, 0.25, 0.06), lamp)
        light(S, "lamp_light_%d" % i, "SPOT", (0, y, WALL_H - 0.15), 380, WARM, 0.3,
              rot=(0, 0, 0), spot=95)
    crate = patterned("crate_wood", (0.30, 0.20, 0.10), (0.20, 0.12, 0.06), "planks", 4.0, 0.8)
    box(S, "crate_a", (w / 2 - 0.6, 0.9, 0.35), (0.7, 0.7, 0.7), crate)
    box(S, "crate_b", (w / 2 - 0.55, 1.65, 0.3), (0.6, 0.6, 0.6), crate)
    box(S, "crate_c", (w / 2 - 0.6, 1.2, 0.95), (0.5, 0.5, 0.5), crate)
    pipe = mat("pipe", (0.25, 0.22, 0.18), 0.4, 0.8)
    cyl(S, "pipe_a", (0, d - 0.05, 2.9), 0.06, w, pipe, 8, rot=(0, math.radians(90), 0))
    cyl(S, "pipe_b", (0, d - 0.05, 2.7), 0.04, w, pipe, 8, rot=(0, math.radians(90), 0))


def room_dressing(S, room):
    w, d = room["size"]
    floor = patterned("dressing_carpet", (0.30, 0.10, 0.06), (0.22, 0.07, 0.05), "checker", 3.0, 0.9)
    wall = patterned("wallpaper", (0.45, 0.32, 0.20), (0.36, 0.24, 0.15), "stripes", 3.0, 0.8)
    wood = mat("vanity_wood", (0.25, 0.12, 0.06), 0.45)
    shell(S, room, floor, wall, wood, mat("door_red", (0.42, 0.03, 0.03), 0.5),
          mat("frame_cream", (0.72, 0.66, 0.52), 0.5))
    mirror = mat("mirror", (0.55, 0.6, 0.62), 0.05, 1.0)
    bulb = mat("bulb", (1, 0.95, 0.8), 0.3, emit=(1, 0.9, 0.7), strength=12)
    for k, x in enumerate((-2.0, 2.0)):
        box(S, "vanity_%d" % k, (x, d - 0.4, 0.42), (1.8, 0.6, 0.84), wood)
        box(S, "mirror_%d" % k, (x, d - 0.03, 1.55), (1.3, 0.04, 1.0), mirror)
        for i in range(5):
            sphere(S, "bulb_%d_%d" % (k, i), (x - 0.6 + i * 0.3, d - 0.07, 2.12), 0.06, bulb, 8)
        light(S, "vanity_light_%d" % k, "AREA", (x, d - 0.4, 2.1), 120, (1, 0.85, 0.6), 1.4,
              rot=(math.radians(20), 0, 0))
        for i in range(4):
            cyl(S, "bottle_%d_%d" % (k, i), (x - 0.5 + i * 0.3, d - 0.45, 0.92), 0.04, 0.16,
                mat("glass_%d" % i, (0.3 + 0.15 * i, 0.15, 0.1), 0.2), 8)
    vase = mat("vase", (0.6, 0.55, 0.45), 0.3)
    petals = mat("roses", (0.6, 0.05, 0.06), 0.8)
    leaves = mat("leaves", (0.08, 0.22, 0.06), 0.8)
    cyl(S, "vase", (-w / 2 + 0.6, d - 0.6, 0.4), 0.18, 0.8, vase, 12)
    for i in range(9):
        a = i * 0.7
        sphere(S, "rose_%d" % i, (-w / 2 + 0.6 + math.cos(a) * 0.25, d - 0.6 + math.sin(a) * 0.25, 0.95 + (i % 3) * 0.1),
               0.1, petals if i % 3 else leaves, 6)
    books = mat("books", (0.2, 0.1, 0.08), 0.8)
    box(S, "bookshelf", (w / 2 - 0.3, d - 1.3, 1.0), (0.5, 1.6, 2.0), wood)
    for s in range(4):
        box(S, "books_%d" % s, (w / 2 - 0.45, d - 1.3, 0.35 + s * 0.48), (0.25, 1.4, 0.3), books)
    box(S, "rack", (-w / 2 + 0.5, 2.0, 1.6), (0.05, 2.0, 0.05), mat("brass", (0.75, 0.55, 0.22), 0.35, 1.0))
    for i in range(5):
        box(S, "costume_%d" % i, (-w / 2 + 0.5, 1.2 + i * 0.4, 1.05), (0.12, 0.32, 1.0),
            mat("costume_%d" % (i % 3), ((0.5, 0.1, 0.1), (0.1, 0.1, 0.3), (0.6, 0.55, 0.4))[i % 3], 0.9))
    light(S, "ceiling_glow", "POINT", (0, d * 0.4, 3.0), 120, WARM, 0.6)


def room_rehearsal(S, room):
    w, d = room["size"]
    floor = patterned("rehearsal_planks", (0.30, 0.17, 0.08), (0.45, 0.27, 0.12), "planks", 2.2, 0.35)
    wall = patterned("rehearsal_wall", (0.20, 0.17, 0.14), (0.14, 0.12, 0.10), "stripes", 1.5, 0.8)
    shell(S, room, floor, wall, mat("dark_wood", (0.12, 0.05, 0.03), 0.5),
          mat("door_red", (0.42, 0.03, 0.03), 0.5), mat("frame_cream", (0.72, 0.66, 0.52), 0.5))
    black = mat("piano_black", (0.015, 0.015, 0.018), 0.15)
    ivory = mat("ivory", (0.85, 0.82, 0.75), 0.3)
    px, py = -2.2, d - 1.6
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=0.35, location=(px, py, 0.85))
    body = bpy.context.active_object
    body.name = "piano_body"
    body.scale = (0.75, 1.0, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    body.data.materials.append(black)
    link(body, S)
    box(S, "piano_keys", (px, py - 1.02, 0.86), (1.4, 0.18, 0.05), ivory)
    box(S, "piano_lid", (px + 0.25, py + 0.1, 1.45), (1.4, 1.9, 0.03), black, math.radians(8))
    for lx, ly in ((-0.55, -0.6), (0.55, -0.6), (0, 0.8)):
        cyl(S, "piano_leg_%.1f" % lx, (px + lx, py + ly, 0.35), 0.06, 0.7, black, 8)
    box(S, "bench", (px, py - 1.6, 0.25), (0.9, 0.35, 0.5), black)
    stand = mat("music_stand", (0.1, 0.1, 0.1), 0.4, 0.8)
    for i in range(3):
        cyl(S, "stand_%d" % i, (1.0 + i * 1.1, d - 1.2, 0.6), 0.02, 1.2, stand, 6)
        box(S, "stand_tray_%d" % i, (1.0 + i * 1.1, d - 1.2, 1.25), (0.45, 0.04, 0.3), stand, 0)
    light(S, "piano_pool", "SPOT", (px, py - 1.0, 4.2), 900, (1.0, 0.82, 0.6), 0.4,
          rot=(math.radians(12), 0, 0), spot=50)
    light(S, "room_fill", "POINT", (2.0, d * 0.5, 3.0), 90, WARM, 0.8)


BUILDERS = {"foyer": room_foyer, "auditorium": room_auditorium, "stage": room_stage,
            "backstage": room_backstage, "dressing": room_dressing, "rehearsal": room_rehearsal}


def build(room_id, force):
    room = next(r for r in ROOMS["rooms"] if r["id"] == room_id)
    path = OUT / ("pe_%s.blend" % room_id)
    if path.exists() and not force:
        raise SystemExit("%s exists and is the authority now; edit it in Blender, or pass --force" % path)
    cols = reset()
    S = cols["TH_SOURCE"]
    BUILDERS[room_id](S, room)
    # TH_RENDER: the same surfaces, joined and unwrapped, receive the bake.
    meshes = [o for o in S.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for o in meshes:
        c = o.copy()
        c.data = o.data.copy()
        cols["TH_RENDER"].objects.link(c)
        copies.append(c)
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    render = bpy.context.active_object
    render.name = "pe_%s_render" % room_id
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    anchor = bpy.data.objects.new("spawn", None)
    anchor.location = (0, 1, 0)
    cols["TH_ANCHORS"].objects.link(anchor)
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print("AUTHORED", path, len(meshes), "source meshes")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--room", action="append", required=True)
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    for r in a.room:
        build(r, a.force)


main()
