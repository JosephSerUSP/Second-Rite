"""Shared furnishing grammar for St. Maria interiors.

St. Maria is a **colonial Portuguese** town, and that is a specific vocabulary,
not a generic "old" one:

- limewashed masonry (*caiacao*) rather than grey plaster or bare brick;
- an *azulejo* dado -- blue-and-white tin-glazed tile as a waist-high band on
  the wall, never as a whole wall;
- dark tropical hardwood, heavy and turned rather than slender;
- wrought iron: grilles over windows, bands on chests, lantern frames;
- terracotta for pantiles, floor tile and unglazed pottery;
- panelled doors and shutters, not plank doors.

Every piece here takes an `Interior` and appends to it, so a map file reads as
a furnishing list. Pieces are deterministic, low-poly and axis-aligned, which
keeps them cheap and keeps the world-space box-projected materials clean.

Placement convention: `at=(x, y)` is the footprint CENTRE on the floor, and
pieces build upward from z=0. Larger x is deeper into the room, away from the
camera; -y is screen right.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Self-sufficient: this module must import cleanly regardless of whether
# `interior` happened to be imported first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import second_rite_asset_core as asset_core  # noqa: E402


def _leg(room, name, x, y, size, height, mat):
    return room.part(name, (size, size, height), (x, y, height / 2.0), mat)


def arca(room, name, at, *, length=1.15, depth=0.55, height=0.58):
    """A banded chest. The workhorse of a colonial interior: storage, seat,
    and the thing a lodger actually owns."""
    x, y = at
    room.part(f"{name}_body", (depth, length, height * 0.78),
              (x, y, height * 0.39), room.wood)
    room.part(f"{name}_lid", (depth + 0.05, length + 0.05, height * 0.22),
              (x, y, height * 0.89), room.wood)
    for index, offset in enumerate((-length * 0.3, length * 0.3)):
        room.part(f"{name}_band_{index}", (depth + 0.07, 0.06, height),
                  (x, y + offset, height / 2.0), room.iron)
    room.part(f"{name}_lock", (0.04, 0.14, 0.12),
              (x - depth / 2.0 - 0.02, y, height * 0.72), room.iron)


def cama(room, name, at, *, length=1.95, width=0.95, height=0.5):
    """A bed with turned posts, headboard toward the back wall."""
    x, y = at
    room.part(f"{name}_frame", (width, length, height * 0.34),
              (x, y, height * 0.5), room.wood)
    room.part(f"{name}_mattress", (width - 0.08, length - 0.1, 0.2),
              (x, y, height + 0.1), room.cloth)
    room.part(f"{name}_bolster", (width - 0.14, 0.3, 0.16),
              (x, y - length / 2.0 + 0.22, height + 0.26), room.cloth)
    room.part(f"{name}_headboard", (0.08, width + 0.06, 0.85),
              (x + width / 2.0, y, 0.62), room.wood)
    for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                      (-0.5, -0.5), (-0.5, 0.5))):
        post = 1.05 if dx > 0 else 0.55
        _leg(room, f"{name}_post_{index}", x + dx * (width - 0.12),
             y + dy * (length - 0.12), 0.09, post, room.wood)


def armario(room, name, at, *, width=1.05, depth=0.5, height=1.85):
    """A panelled cabinet. Tall, dark and heavy: the room's vertical mass."""
    x, y = at
    room.part(f"{name}_carcass", (depth, width, height), (x, y, height / 2.0),
              room.wood)
    room.part(f"{name}_cornice", (depth + 0.09, width + 0.09, 0.1),
              (x, y, height + 0.05), room.wood)
    for index, offset in enumerate((-width * 0.24, width * 0.24)):
        room.part(f"{name}_panel_{index}", (0.03, width * 0.38, height * 0.62),
                  (x - depth / 2.0 - 0.015, y + offset, height * 0.55), room.wood)
    room.part(f"{name}_handle", (0.05, 0.05, 0.16),
              (x - depth / 2.0 - 0.04, y, height * 0.55), room.iron)


def mesa(room, name, at, *, length=1.25, width=0.7, height=0.76):
    """A table on turned legs."""
    x, y = at
    room.part(f"{name}_top", (width, length, 0.07), (x, y, height), room.wood)
    room.part(f"{name}_rail", (width - 0.14, length - 0.14, 0.09),
              (x, y, height - 0.11), room.wood)
    for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                      (-0.5, -0.5), (-0.5, 0.5))):
        _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.14),
             y + dy * (length - 0.14), 0.08, height - 0.04, room.wood)


def cadeira(room, name, at, *, seat=0.44, width=0.44):
    """A straight-backed chair."""
    x, y = at
    room.part(f"{name}_seat", (width, width, 0.06), (x, y, seat), room.wood)
    room.part(f"{name}_back", (0.06, width, 0.52),
              (x + width / 2.0 - 0.03, y, seat + 0.28), room.wood)
    for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                      (-0.5, -0.5), (-0.5, 0.5))):
        _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.08),
             y + dy * (width - 0.08), 0.05, seat, room.wood)


def pote(room, name, at, *, height=0.46, radius=0.19, sides=8, mat=None):
    """An unglazed jar. Radial, so it breaks up an interior of boxes."""
    import bmesh

    x, y = at
    bm = bmesh.new()
    profile = ((0.55, 0.0), (1.0, 0.28), (0.86, 0.62), (0.48, 0.9), (0.58, 1.0))
    rings = []
    for scale, level in profile:
        ring = [bm.verts.new((math.cos(math.tau * i / sides) * radius * scale,
                              math.sin(math.tau * i / sides) * radius * scale,
                              level * height)) for i in range(sides)]
        rings.append(ring)
    bm.faces.new(reversed(rings[0]))
    for lower, upper in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
    bm.faces.new(rings[-1])
    obj = asset_core.mesh_object_from_bmesh(name, bm)
    asset_core.parent_local(obj, room.root, loc=(x, y, 0.0))
    asset_core.assign_material(obj, mat or room.terracotta)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    return obj


def prateleira(room, name, *, y, z, length=1.3, depth=0.26):
    """A shelf against the back wall, with its brackets."""
    x = room.back_x - depth / 2.0
    room.part(f"{name}_board", (depth, length, 0.05), (x, y, z), room.wood)
    for index, offset in enumerate((-length * 0.36, length * 0.36)):
        room.part(f"{name}_bracket_{index}", (depth * 0.7, 0.05, 0.16),
                  (x + 0.03, y + offset, z - 0.1), room.iron)


def lanterna(room, name, *, y, z=2.1, energy=13.0):
    """A wrought-iron wall lantern, and the light it actually casts."""
    x = room.back_x - 0.16
    room.part(f"{name}_bracket", (0.22, 0.05, 0.05), (x + 0.08, y, z + 0.18),
              room.iron)
    room.part(f"{name}_cage", (0.16, 0.16, 0.22), (x, y, z), room.iron)
    room.part(f"{name}_flame", (0.09, 0.09, 0.13), (x, y, z), room.lamplight)
    return room.light(name, "POINT", (x - 0.05, y, z), (0.0, 0.0, -1.0),
                      energy, (1.0, 0.82, 0.55), radius=0.14)


def _cylinder(room, name, at, *, radius, height, mat, sides=10):
    """Low-poly vertical cylinder with its origin on the floor."""
    import bmesh

    x, y = at
    bm = bmesh.new()
    bottom = []
    top = []
    for index in range(sides):
        angle = math.tau * index / sides
        point = (math.cos(angle) * radius, math.sin(angle) * radius)
        bottom.append(bm.verts.new((point[0], point[1], 0.0)))
        top.append(bm.verts.new((point[0], point[1], height)))
    bm.faces.new(reversed(bottom))
    for index in range(sides):
        nxt = (index + 1) % sides
        bm.faces.new((bottom[index], bottom[nxt], top[nxt], top[index]))
    bm.faces.new(top)
    obj = asset_core.mesh_object_from_bmesh(name, bm)
    asset_core.parent_local(obj, room.root, loc=(x, y, 0.0))
    asset_core.assign_material(obj, mat)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    return obj


def forno(room, name, at, *, width=1.7, depth=0.95, height=1.65):
    """A masonry bread oven: thick body, dark mouth and a tiled crown."""
    x, y = at
    body_h = height * 0.72
    room.part(f"{name}_body", (depth, width, body_h),
              (x, y, body_h / 2.0), room.terracotta)
    room.part(f"{name}_crown", (depth + 0.08, width + 0.08, 0.28),
              (x, y, body_h + 0.14), room.terracotta)
    room.part(f"{name}_lintel", (depth + 0.04, width * 0.72, 0.18),
              (x - depth / 2.0 - 0.02, y, body_h * 0.72), room.terracotta)
    room.part(f"{name}_mouth", (0.055, width * 0.58, body_h * 0.47),
              (x - depth / 2.0 - 0.04, y, body_h * 0.40), room.charcoal)
    room.part(f"{name}_hearth", (depth + 0.14, width * 0.72, 0.10),
              (x - depth * 0.20, y, 0.05), room.terracotta)
    room.part(f"{name}_ash", (0.06, width * 0.34, 0.18),
              (x - depth / 2.0 - 0.07, y, 0.17), room.charcoal)
    room.part(f"{name}_fire", (0.07, width * 0.34, body_h * 0.20),
              (x - depth / 2.0 - 0.08, y, body_h * 0.38), room.firelight)
    return room.light(f"{name}_firelight", "POINT",
                      (x - depth / 2.0 - 0.15, y, body_h * 0.38),
                      (1.0, 0.0, -0.35), 42.0, (1.0, 0.36, 0.10), radius=0.20)


def bread_loaf(room, name, at, *, length=0.48, width=0.28, height=0.19,
               rotation=0.0):
    """A scored, deliberately chunky loaf that reads at native resolution."""
    x, y = at
    room.part(f"{name}_body", (height, length, width),
              (x, y, width / 2.0 + 0.04), room.bread_crust,
              rotation=(0.0, 0.0, rotation))
    for index in range(2):
        room.part(f"{name}_score_{index}", (height + 0.012, 0.045, 0.012),
                  (x - height / 2.0 - 0.008, y + (index - 0.5) * length * 0.28,
                   width * 0.74), room.whitewash,
                  rotation=(0.0, 0.0, rotation))


def bread_display(room, name, at, *, length=1.15, depth=0.42, loaves=4):
    """A low display board with a row of distinct baked goods."""
    x, y = at
    room.part(f"{name}_board", (depth, length, 0.08), (x, y, 0.82), room.wood)
    for index in range(loaves):
        offset = (index - (loaves - 1) / 2.0) * (length / max(loaves, 1))
        bread_loaf(room, f"{name}_loaf_{index}", (x - 0.03, y + offset),
                   rotation=0.12 * (index - 1))


def sack(room, name, at, *, height=0.85, radius=0.34):
    """A tied flour sack, an authored vertical mass rather than a cube."""
    x, y = at
    _cylinder(room, f"{name}_body", (x, y), radius=radius, height=height,
              mat=room.cloth, sides=10)
    room.part(f"{name}_tie", (0.10, 0.10, 0.12), (x, y, height + 0.06),
              room.iron)
    room.part(f"{name}_fold", (0.05, radius * 1.35, 0.10),
              (x - radius * 0.35, y, height * 0.82), room.cloth)


def barrel(room, name, at, *, radius=0.38, height=0.82, mat=None):
    """A small stave barrel with two iron hoops."""
    x, y = at
    _cylinder(room, f"{name}_body", (x, y), radius=radius, height=height,
              mat=mat or room.wood, sides=12)
    for index, z in enumerate((height * 0.24, height * 0.76)):
        _cylinder(room, f"{name}_hoop_{index}", (x, y), radius=radius + 0.025,
                  height=0.045, mat=room.iron, sides=12)
        room.parts[-1].location.z = z
    return room.parts[-3]


def anvil(room, name, at, *, width=0.92, height=0.82, face_mat=None):
    """A squat, readable anvil with a horn extending toward the aisle."""
    x, y = at
    room.part(f"{name}_base", (0.62, width * 0.64, 0.22),
              (x, y, 0.11), room.forge_scale)
    room.part(f"{name}_waist", (0.38, width * 0.42, height * 0.55),
              (x, y, height * 0.40), room.forge_scale)
    room.part(f"{name}_face", (0.52, width, 0.16),
              (x - 0.04, y, height * 0.80), face_mat or room.forge_scale)
    _cylinder(room, f"{name}_horn", (x - 0.34, y), radius=0.18,
              height=0.48, mat=room.forge_scale, sides=8)
    room.parts[-1].rotation_euler[1] = math.radians(90.0)
    room.parts[-1].location.z = height * 0.72
    room.part(f"{name}_hole", (0.12, 0.12, 0.025),
              (x + 0.12, y, height * 0.895), room.charcoal)


def forge_hearth(room, name, at, *, width=1.25, depth=0.92, height=0.76):
    """A stone hearth with a contained coal bed and visible fire."""
    x, y = at
    room.part(f"{name}_stone", (depth, width, height),
              (x, y, height / 2.0), room.stone)
    room.part(f"{name}_coal", (depth * 0.72, width * 0.64, 0.10),
              (x - depth * 0.10, y, height + 0.05), room.charcoal)
    room.part(f"{name}_fire", (0.08, width * 0.42, 0.28),
              (x - depth * 0.50, y, height + 0.20), room.firelight)
    return room.light(f"{name}_light", "POINT",
                      (x - depth * 0.48, y, height + 0.18),
                      (1.0, 0.0, -0.30), 95.0, (1.0, 0.30, 0.08), radius=0.20)


def bellows(room, name, at, *, length=0.95, width=0.50, height=0.42):
    """Wood-and-cloth bellows aimed at a hearth."""
    x, y = at
    room.part(f"{name}_body", (length, width, height),
              (x, y, height * 0.62), room.wood,
              rotation=(0.0, math.radians(-10.0), 0.0))
    room.part(f"{name}_cloth", (length * 0.56, width + 0.04, height * 0.66),
              (x - length * 0.14, y, height * 0.83), room.cloth,
              rotation=(0.0, math.radians(-10.0), 0.0))
    room.part(f"{name}_handle", (0.32, 0.07, 0.07),
              (x + length * 0.58, y, height * 0.90), room.wood)


def quench_trough(room, name, at, *, length=1.25, width=0.58, height=0.52):
    """A deep trough with a dark water surface and a worn rim."""
    x, y = at
    room.part(f"{name}_body", (width, length, height),
              (x, y, height / 2.0), room.wood)
    room.part(f"{name}_water", (width - 0.12, length - 0.16, 0.05),
              (x - 0.02, y, height - 0.06), room.daylight)
    room.part(f"{name}_rim", (width + 0.08, length + 0.08, 0.08),
              (x, y, height), room.forge_scale)


def weapon_rack(room, name, *, y, z=1.18, length=1.5, blades=3):
    """Wall rack for unfinished tools and opening weapons."""
    x = room.back_x - 0.18
    room.part(f"{name}_rail", (0.10, length, 0.12), (x, y, z), room.wood)
    for index in range(blades):
        offset = (index - (blades - 1) / 2.0) * (length / max(blades, 1))
        room.part(f"{name}_blade_{index}", (0.06, 0.12, 0.90),
                  (x - 0.08, y + offset, z + 0.50), room.forge_scale)
        room.part(f"{name}_grip_{index}", (0.10, 0.18, 0.20),
                  (x - 0.12, y + offset, z - 0.10), room.wood)


def azulejo_dado(room, *, height=1.15, y0=None, y1=None, proud=0.02,
                 margin=0.06):
    """The tiled band along the back wall, broken around every opening.

    Waist-high, and only ever a band. A whole wall of azulejo reads as a church
    or a station, not a room somebody lives in.

    Tiling is applied to a WALL, so it stops at each doorway and starts again
    on the far side. Running one band across the openings makes the doors look
    painted on; `room.openings` (recorded by `Interior.back_wall`) is the same
    list the wall itself was built from, so the two can never disagree.
    """
    y0 = -room.half_width if y0 is None else y0
    y1 = room.half_width if y1 is None else y1
    x = room.back_x - proud / 2.0

    # Only openings that actually reach into the band interrupt it; a window
    # sill well above the dado does not.
    blockers = sorted((max(y0, oy0 - margin), min(y1, oy1 + margin))
                      for oy0, oy1, oz0, _oz1 in room.openings
                      if oz0 < height and oy1 > y0 and oy0 < y1)

    cursor, spans = y0, []
    for start, end in blockers:
        if start > cursor:
            spans.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < y1:
        spans.append((cursor, y1))

    for index, (a, b) in enumerate(spans):
        if b - a < 0.05:
            continue
        room.part(f"azulejo_dado_{index}", (proud, b - a, height),
                  (x, (a + b) / 2.0, height / 2.0), room.azulejo)
        room.part(f"azulejo_rail_{index}", (proud + 0.04, b - a, 0.06),
                  (x - 0.01, (a + b) / 2.0, height + 0.03), room.wood)


def janela(room, name, y0, y1, z0, z1, *, grille=True, shutters=True):
    """Window dressing: an iron grille, and shutters folded back."""
    x = room.back_x - 0.04
    cy = (y0 + y1) / 2.0
    if grille:
        for index in range(3):
            gy = y0 + (y1 - y0) * (index + 1) / 4.0
            room.part(f"{name}_bar_{index}", (0.04, 0.035, z1 - z0),
                      (x, gy, (z0 + z1) / 2.0), room.iron)
        room.part(f"{name}_bar_mid", (0.04, y1 - y0, 0.035),
                  (x, cy, (z0 + z1) / 2.0), room.iron)
    if shutters:
        span = y1 - y0
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_shutter_{index}", (0.05, span * 0.34, z1 - z0),
                      (x - 0.1, cy + side * (span * 0.5 + span * 0.17),
                       (z0 + z1) / 2.0), room.wood)


def escada(room, name, *, y, x_start, steps=7, rise=0.19, run=0.3, width=1.5,
           direction=-1.0):
    """A flight of steps going DOWN, away from the floor plane.

    The way out of a storey. `direction` is the axis the flight travels:
    -1 steps toward the camera, +1 steps away from it. At this camera a flight
    running toward the viewer disappears under the status menu almost at once,
    so a visible stair down normally runs AWAY, through an opening.
    """
    for index in range(steps):
        top = -rise * index
        x = x_start + direction * run * index
        room.part(f"{name}_tread_{index}", (run, width, rise + 0.02),
                  (x, y, top - (rise + 0.02) / 2.0), room.wood)
    return x_start + direction * run * (steps - 1), -rise * (steps - 1)
