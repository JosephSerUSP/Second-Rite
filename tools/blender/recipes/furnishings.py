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


# ==========================================================================
# Bakery & Merchant Provisions Grammar
# ==========================================================================

def balcao(room, name, at, *, length=1.8, width=0.68, height=0.88, panels=3):
    """A Portuguese merchant shop counter (*balcão*).

    Heavy dark timber carcass with front recessed paneling, overhanging
    countertop slab, and rear shelving for goods and cash box.
    """
    x, y = at
    # Main carcass
    room.part(f"{name}_carcass", (width * 0.88, length * 0.94, height * 0.88),
              (x, y, height * 0.44), room.wood)
    # Overhang top counter
    room.part(f"{name}_top", (width, length, 0.08),
              (x, y, height + 0.04), room.wood)
    # Plinth base
    room.part(f"{name}_plinth", (width * 0.92, length * 0.96, 0.10),
              (x, y, 0.05), room.wood)
    # Front decorative panels (facing -X towards customer/camera)
    panel_w = (length * 0.8) / panels
    panel_h = height * 0.58
    front_x = x - (width * 0.88) / 2.0 - 0.015
    for i in range(panels):
        py = y - (length * 0.8) / 2.0 + panel_w * (i + 0.5)
        room.part(f"{name}_panel_{i}", (0.03, panel_w * 0.82, panel_h),
                  (front_x, py, height * 0.52), room.wood)


def forno_lenha(room, name, at, *, length=1.5, depth=1.3, height=1.6):
    """A traditional masonry wood-fired bread oven (*forno a lenha*).

    Built with a thick rough stone/brick base, an arched clay baking chamber,
    an open mouth revealing glowing coals, a wood storage niche below, and a
    rising terracotta flue.
    """
    x, y = at
    # Stone lower base
    base_h = 0.72
    room.part(f"{name}_base", (depth, length, base_h),
              (x, y, base_h / 2.0), room.stone)
    # Arched firewood niche underneath (ash/log recess)
    room.part(f"{name}_log_niche", (depth * 0.7, length * 0.5, base_h * 0.65),
              (x - depth * 0.16, y, base_h * 0.35), room.whitewash)
    for i, offset in enumerate((-0.18, 0.0, 0.18)):
        room.part(f"{name}_fuel_log_{i}", (depth * 0.55, 0.12, 0.10),
                  (x - depth * 0.15, y + offset, 0.08), room.wood)

    # Upper baking dome / vault
    dome_h = height - base_h
    room.part(f"{name}_dome", (depth * 0.92, length * 0.92, dome_h),
              (x, y, base_h + dome_h / 2.0), room.terracotta)

    # Arched oven mouth (facing -X towards shop room)
    mouth_w = length * 0.44
    mouth_h = dome_h * 0.62
    mouth_x = x - (depth * 0.92) / 2.0 - 0.02
    mouth_z = base_h + mouth_h / 2.0 + 0.08
    room.part(f"{name}_mouth_frame", (0.08, mouth_w + 0.16, mouth_h + 0.14),
              (mouth_x + 0.02, y, mouth_z), room.stone)
    # Glowing ember bed inside the mouth
    room.part(f"{name}_embers", (0.35, mouth_w * 0.85, 0.12),
              (mouth_x + 0.22, y, base_h + 0.06), room.embers)

    # Terracotta chimney flue rising to ceiling
    chimney_h = 1.6
    room.part(f"{name}_chimney", (0.32, 0.32, chimney_h),
              (x + depth * 0.25, y, height + chimney_h / 2.0), room.terracotta)


def saco(room, name, at, *, width=0.46, depth=0.42, height=0.58, rotation=0.0):
    """A burlap/linen sack of flour or grain with a gathered neck and tied top."""
    import bmesh
    x, y = at
    bm = bmesh.new()
    # 8-sided rounded sack body profiles
    sides = 8
    profile = ((0.75, 0.0), (1.05, 0.32), (0.98, 0.65), (0.65, 0.88), (0.72, 1.0))
    rings = []
    for scale, level in profile:
        ring = [bm.verts.new((math.cos(math.tau * i / sides) * (depth / 2.0) * scale,
                              math.sin(math.tau * i / sides) * (width / 2.0) * scale,
                              level * height)) for i in range(sides)]
        rings.append(ring)
    bm.faces.new(reversed(rings[0]))
    for lower, upper in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
    bm.faces.new(rings[-1])
    obj = asset_core.mesh_object_from_bmesh(name, bm)
    asset_core.parent_local(obj, room.root, loc=(x, y, 0.0),
                            rot=(0.0, 0.0, rotation))
    asset_core.assign_material(obj, room.cloth)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    # Tie string / neck collar
    room.part(f"{name}_tie", (depth * 0.72, width * 0.72, 0.04),
              (x, y, height * 0.88), room.straw)
    return obj


def sacos_pilha(room, name, at, count=3):
    """A leaning cluster / stack of burlap flour and grain sacks."""
    x, y = at
    offsets = [
        (0.0, 0.0, 0.0),
        (0.22, 0.35, 0.25),
        (-0.20, -0.32, -0.35),
    ]
    for i in range(min(count, len(offsets))):
        dx, dy, rot = offsets[i]
        saco(room, f"{name}_{i}", (x + dx, y + dy), rotation=rot)


def cesto_paes(room, name, at, *, radius=0.22, height=0.14, mat_loaves=None):
    """A woven bread basket / wooden crate filled with crusty broas."""
    import bmesh
    x, y = at
    bm = bmesh.new()
    sides = 8
    profile = ((0.80, 0.0), (1.05, 0.5), (1.18, 1.0))
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
    asset_core.assign_material(obj, room.straw)
    asset_core.flat_shade(obj)
    room.parts.append(obj)

    # Loaves inside basket
    loaf_mat = mat_loaves or room.terracotta
    room.part(f"{name}_loaf_0", (0.16, 0.16, 0.11), (x - 0.06, y - 0.05, height + 0.04), loaf_mat)
    room.part(f"{name}_loaf_1", (0.15, 0.15, 0.10), (x + 0.07, y + 0.04, height + 0.03), loaf_mat)
    room.part(f"{name}_loaf_2", (0.14, 0.14, 0.10), (x - 0.02, y + 0.08, height + 0.05), loaf_mat)
    return obj


def pa_forno(room, name, at, *, length=1.75, angle_deg=14.0):
    """A wooden baker's peel (*pá de forno*) leaning against wall or oven."""
    x, y = at
    rad = math.radians(angle_deg)
    # Long round timber pole
    room.part(f"{name}_handle", (0.05, 0.05, length),
              (x + math.sin(rad) * length * 0.45, y, math.cos(rad) * length * 0.5),
              room.wood, rotation=(0.0, rad, 0.0))
    # Flat paddle blade at base
    room.part(f"{name}_blade", (0.34, 0.28, 0.03),
              (x, y, 0.16), room.wood)


def garrafao(room, name, at, *, height=0.52, radius=0.18):
    """A wicker-cased glass demijohn / large olive oil carboy."""
    import bmesh
    x, y = at
    bm = bmesh.new()
    sides = 8
    profile = ((0.65, 0.0), (1.1, 0.35), (0.95, 0.75), (0.35, 0.88), (0.38, 1.0))
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
    asset_core.assign_material(obj, room.straw)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    # Glass neck top
    room.part(f"{name}_cork", (0.09, 0.09, 0.08), (x, y, height + 0.03), room.wood)
    return obj


def balanca(room, name, at, *, height=0.42, width=0.38):
    """A tabletop brass balance scale for weighing dry goods and coins."""
    x, y = at
    # Stand and central pillar
    room.part(f"{name}_base", (0.16, 0.16, 0.04), (x, y, 0.02), room.iron)
    room.part(f"{name}_pillar", (0.04, 0.04, height), (x, y, height / 2.0), room.iron)
    # Cross beam
    room.part(f"{name}_beam", (0.03, width, 0.03), (x, y, height - 0.02), room.bronze)
    # Hanging pans (left and right)
    for i, side in enumerate((-1.0, 1.0)):
        pan_y = y + side * (width / 2.0 - 0.04)
        room.part(f"{name}_string_{i}", (0.015, 0.015, height * 0.45),
                  (x, pan_y, height * 0.65), room.iron)
        room.part(f"{name}_pan_{i}", (0.12, 0.12, 0.02),
                  (x, pan_y, height * 0.42), room.bronze)


# ==========================================================================
# Blacksmith Forge & Armory Grammar
# ==========================================================================

def forja(room, name, at, *, length=1.8, depth=1.1, height=0.86, chimney_h=2.3):
    """A heavy masonry blacksmith forge hearth (*forja*).

    Rough stone masonry body, firebrick-lined coal bed with glowing coke
    embers, iron hood, and overhead chimney flue.
    """
    x, y = at
    # Heavy stone masonry foundation
    room.part(f"{name}_masonry", (depth, length, height),
              (x, y, height / 2.0), room.stone)
    # Top hearth rim border
    room.part(f"{name}_rim_front", (0.14, length + 0.06, 0.10),
              (x - depth / 2.0 + 0.07, y, height + 0.05), room.stone)
    room.part(f"{name}_rim_side0", (depth, 0.14, 0.10),
              (x, y - length / 2.0 + 0.07, height + 0.05), room.stone)
    room.part(f"{name}_rim_side1", (depth, 0.14, 0.10),
              (x, y + length / 2.0 - 0.07, height + 0.05), room.stone)

    # Charcoal fire bed with incandescent embers
    room.part(f"{name}_embers", (depth * 0.72, length * 0.65, 0.14),
              (x + 0.05, y, height + 0.04), room.embers)

    # Iron hood over hearth
    hood_z = height + 1.1
    room.part(f"{name}_hood", (depth * 0.85, length * 0.85, 0.55),
              (x + 0.05, y, hood_z), room.iron)
    # Chimney flue rising up
    room.part(f"{name}_chimney", (0.42, 0.42, chimney_h),
              (x + depth * 0.22, y, hood_z + chimney_h / 2.0 + 0.25), room.stone)


def bigorna(room, name, at, *, horn_len=0.78, width=0.26, height=0.44, stump_h=0.46):
    """A traditional blacksmith anvil (*bigorna*) mounted on a tree stump.

    Hardened iron anvil body with tapered horn, flat striking table, and
    waist, secured onto a massive banded hardwood stump (*cepo*).
    """
    x, y = at
    # Hardwood tree stump base
    stump_dia = max(width * 1.8, 0.48)
    room.part(f"{name}_stump", (stump_dia, stump_dia, stump_h),
              (x, y, stump_h / 2.0), room.wood)
    # Wrought iron retaining band around stump
    room.part(f"{name}_stump_band", (stump_dia + 0.04, stump_dia + 0.04, 0.06),
              (x, y, stump_h * 0.75), room.iron)

    # Anvil base foot
    az = stump_h
    room.part(f"{name}_foot", (width * 1.15, horn_len * 0.62, 0.08),
              (x, y, az + 0.04), room.iron)
    # Anvil waist
    room.part(f"{name}_waist", (width * 0.65, horn_len * 0.42, height * 0.45),
              (x, y, az + 0.08 + height * 0.225), room.iron)
    # Main flat striking table (body)
    room.part(f"{name}_table", (width, horn_len * 0.65, height * 0.42),
              (x, y + horn_len * 0.08, az + height * 0.78), room.iron)
    # Conical horn extending to one side (-Y direction)
    room.part(f"{name}_horn", (width * 0.68, horn_len * 0.38, height * 0.32),
              (x, y - horn_len * 0.38, az + height * 0.78), room.iron)


def tina(room, name, at, *, radius=0.32, height=0.56):
    """A staved wooden quench tub / slack tub (*tina de têmpera*) with iron hoops."""
    import bmesh
    x, y = at
    bm = bmesh.new()
    sides = 10
    profile = ((0.90, 0.0), (1.08, 0.5), (1.14, 1.0))
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
    asset_core.assign_material(obj, room.wood)
    asset_core.flat_shade(obj)
    room.parts.append(obj)

    # Iron reinforcement hoops
    for i, h_frac in enumerate((0.25, 0.82)):
        room.part(f"{name}_hoop_{i}", (radius * 2.3, radius * 2.3, 0.04),
                  (x, y, height * h_frac), room.iron)
    # Water surface inside tub
    room.part(f"{name}_water", (radius * 1.9, radius * 1.9, 0.02),
              (x, y, height * 0.90), room.iron)
    return obj


def fole(room, name, at, *, length=1.1, width=0.52, height=0.38):
    """A heavy leather and dark wood blacksmith bellows (*fole*)."""
    x, y = at
    # Wooden top and bottom boards
    room.part(f"{name}_board_bot", (length * 0.85, width, 0.05),
              (x, y, 0.08), room.wood)
    room.part(f"{name}_board_top", (length * 0.85, width, 0.05),
              (x, y, height), room.wood)
    # Leather accordion body
    room.part(f"{name}_leather", (length * 0.78, width * 0.92, height - 0.12),
              (x, y, height / 2.0 + 0.02), room.cloth)
    # Iron nozzle / tuyere pipe connecting into the forge
    room.part(f"{name}_pipe", (length * 0.45, 0.08, 0.08),
              (x - length * 0.55, y, 0.18), room.iron)
    # Operating handle
    room.part(f"{name}_handle", (0.55, 0.06, 0.06),
              (x + length * 0.55, y, height + 0.08), room.wood)


def suporte_armas(room, name, at, *, length=1.65, depth=0.45, height=1.75):
    """An armory weapon display rack holding forged swords, spears and shields."""
    x, y = at
    # Vertical posts
    for i, side in enumerate((-1.0, 1.0)):
        py = y + side * (length / 2.0 - 0.06)
        room.part(f"{name}_post_{i}", (0.09, 0.09, height),
                  (x, py, height / 2.0), room.wood)
        room.part(f"{name}_foot_{i}", (depth, 0.09, 0.08),
                  (x, py, 0.04), room.wood)
    # Cross rails
    for i, z_lvl in enumerate((height * 0.35, height * 0.85)):
        room.part(f"{name}_rail_{i}", (0.06, length, 0.08),
                  (x, y, z_lvl), room.wood)

    # Forged broadswords resting vertically
    for i, offset in enumerate((-0.45, -0.15, 0.15)):
        sy = y + offset
        # Blade
        room.part(f"{name}_sword_blade_{i}", (0.03, 0.07, 0.95),
                  (x - 0.04, sy, height * 0.58), room.iron)
        # Crossguard and pommel
        room.part(f"{name}_sword_guard_{i}", (0.05, 0.22, 0.04),
                  (x - 0.04, sy, height * 0.58 + 0.48), room.iron)
        room.part(f"{name}_sword_grip_{i}", (0.03, 0.03, 0.20),
                  (x - 0.04, sy, height * 0.58 + 0.60), room.wood)

    # Shield blank leaning against right post
    room.part(f"{name}_shield", (0.05, 0.48, 0.65),
              (x - 0.08, y + length / 2.0 - 0.22, height * 0.42), room.wood,
              rotation=(0.0, 0.12, 0.0))
    room.part(f"{name}_shield_boss", (0.09, 0.12, 0.12),
              (x - 0.12, y + length / 2.0 - 0.22, height * 0.42), room.iron)


def suporte_ferramentas(room, name, *, y, z, length=1.3):
    """A wall-mounted tool rail holding blacksmith tongs and hammers."""
    x = room.back_x - 0.06
    # Timber backing batten
    room.part(f"{name}_batten", (0.04, length, 0.10),
              (x, y, z), room.wood)
    # Iron pegs & tools hanging
    for i, offset in enumerate((-0.42, -0.14, 0.14, 0.42)):
        ty = y + offset
        room.part(f"{name}_peg_{i}", (0.16, 0.02, 0.02),
                  (x - 0.08, ty, z), room.iron)
        # Hanging hammer or tongs
        if i % 2 == 0:
            room.part(f"{name}_hammer_handle_{i}", (0.03, 0.03, 0.45),
                      (x - 0.12, ty, z - 0.24), room.wood)
            room.part(f"{name}_hammer_head_{i}", (0.08, 0.14, 0.06),
                      (x - 0.12, ty, z - 0.45), room.iron)
        else:
            room.part(f"{name}_tongs_{i}", (0.04, 0.06, 0.55),
                      (x - 0.12, ty, z - 0.28), room.iron)


def pilha_lingotes(room, name, at, rows=3, cols=2):
    """A stack of heavy cast iron and bronze ingots."""
    x, y = at
    ingot_l, ingot_w, ingot_h = 0.32, 0.14, 0.07
    for r in range(rows):
        for c in range(cols):
            ix = x + (c - cols / 2.0 + 0.5) * (ingot_w + 0.02)
            iy = y + (r % 2) * 0.04
            iz = r * ingot_h + ingot_h / 2.0
            mat = room.bronze if (r + c) % 3 == 0 else room.iron
            room.part(f"{name}_ingot_{r}_{c}", (ingot_w, ingot_l, ingot_h),
                      (ix, iy, iz), mat)


def barril(room, name, at, *, radius=0.32, height=0.76):
    """A traditional staved storage barrel with iron reinforcement hoops."""
    import bmesh
    x, y = at
    bm = bmesh.new()
    sides = 10
    profile = ((0.86, 0.0), (1.08, 0.5), (0.86, 1.0))
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
    asset_core.assign_material(obj, room.wood)
    asset_core.flat_shade(obj)
    room.parts.append(obj)

    # 3 Iron hoops
    for i, h_frac in enumerate((0.18, 0.50, 0.82)):
        room.part(f"{name}_hoop_{i}", (radius * 2.22, radius * 2.22, 0.04),
                  (x, y, height * h_frac), room.iron)
    return obj


def bancada(room, name, at, *, length=1.65, width=0.68, height=0.86):
    """A heavy-duty timber smith's workbench with vise and bottom shelf."""
    x, y = at
    # Sturdy tabletop
    room.part(f"{name}_top", (width, length, 0.09),
              (x, y, height), room.wood)
    # Heavy 4 legs
    for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                      (-0.5, -0.5), (-0.5, 0.5))):
        _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.16),
             y + dy * (length - 0.16), 0.10, height - 0.045, room.wood)
    # Bottom tool shelf
    room.part(f"{name}_shelf", (width - 0.16, length - 0.16, 0.04),
              (x, y, 0.22), room.wood)
    # Mounted iron bench vice on left front corner
    room.part(f"{name}_vice_base", (0.16, 0.16, 0.10),
              (x - width / 2.0 + 0.08, y - length / 2.0 + 0.12, height + 0.09), room.iron)
    room.part(f"{name}_vice_jaw", (0.08, 0.18, 0.12),
              (x - width / 2.0 + 0.04, y - length / 2.0 + 0.12, height + 0.18), room.iron)
