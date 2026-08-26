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

That vocabulary lives in the PROPORTIONS, MATERIALS and JOINERY, which is where
it is load-bearing -- not in the identifiers. Pieces are named in English; a
Portuguese term is kept only where English needs a phrase to say the same thing
(`azulejo` is not "tile", it is waist-high blue-and-white tin-glaze). A
`cadeira` and a `chair` are the same chair, and the name does not make either
one Portuguese: the hardwood, the turning and the iron banding do. The prose
below still names the Portuguese term wherever it helps identify the object.

Every piece here takes an `Interior` and appends to it, so a map file reads as
a furnishing list. Pieces are deterministic, low-poly and axis-aligned, which
keeps them cheap and keeps the world-space box-projected materials clean.

Each piece builds inside `Interior.piece`, so it lands in the `.blend` as ONE
joined object rather than as its component boxes. The `.blend` is the
hand-editable source document and a furnished shop is otherwise ~100 loose
boxes in a flat outliner.

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


def _revolved(room, name, at, radii, profile, *, mat, sides=8, rotation=0.0):
    """A radial solid swept from a (scale, level) profile.

    Jars, sacks, barrels and tubs are all this shape with different numbers,
    and radial pieces are what stop an interior reading as a room of boxes.
    `radii` is (rx, ry) so a sack can be slightly oval without a scale on the
    object, which would fight the world-space box projection.
    """
    import bmesh

    x, y = at
    rx, ry = radii
    bm = bmesh.new()
    rings = []
    for scale, level in profile:
        ring = [bm.verts.new((math.cos(math.tau * i / sides) * rx * scale,
                              math.sin(math.tau * i / sides) * ry * scale,
                              level)) for i in range(sides)]
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
    asset_core.assign_material(obj, mat)
    asset_core.flat_shade(obj)
    room.parts.append(obj)
    return obj


# ---------------------------------------------------------------------------
# Domestic
# ---------------------------------------------------------------------------

def chest(room, name, at, *, length=1.15, depth=0.55, height=0.58):
    """A banded chest (*arca*). The workhorse of a colonial interior: storage,
    seat, and the thing a lodger actually owns."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_body", (depth, length, height * 0.78),
                  (x, y, height * 0.39), room.wood)
        room.part(f"{name}_lid", (depth + 0.05, length + 0.05, height * 0.22),
                  (x, y, height * 0.89), room.wood)
        for index, offset in enumerate((-length * 0.3, length * 0.3)):
            room.part(f"{name}_band_{index}", (depth + 0.07, 0.06, height),
                      (x, y + offset, height / 2.0), room.iron)
        room.part(f"{name}_lock", (0.04, 0.14, 0.12),
                  (x - depth / 2.0 - 0.02, y, height * 0.72), room.iron)


def bed(room, name, at, *, length=1.95, width=0.95, height=0.5):
    """A bed with turned posts, headboard toward the back wall."""
    x, y = at
    with room.piece(name):
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


def cabinet(room, name, at, *, width=1.05, depth=0.5, height=1.85):
    """A panelled cabinet (*armario*). Tall, dark and heavy: the room's
    vertical mass."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_carcass", (depth, width, height),
                  (x, y, height / 2.0), room.wood)
        room.part(f"{name}_cornice", (depth + 0.09, width + 0.09, 0.1),
                  (x, y, height + 0.05), room.wood)
        for index, offset in enumerate((-width * 0.24, width * 0.24)):
            room.part(f"{name}_panel_{index}",
                      (0.03, width * 0.38, height * 0.62),
                      (x - depth / 2.0 - 0.015, y + offset, height * 0.55),
                      room.wood)
        room.part(f"{name}_handle", (0.05, 0.05, 0.16),
                  (x - depth / 2.0 - 0.04, y, height * 0.55), room.iron)


def table(room, name, at, *, length=1.25, width=0.7, height=0.76):
    """A table on turned legs."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.07), (x, y, height),
                  room.wood)
        room.part(f"{name}_rail", (width - 0.14, length - 0.14, 0.09),
                  (x, y, height - 0.11), room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.14),
                 y + dy * (length - 0.14), 0.08, height - 0.04, room.wood)


def chair(room, name, at, *, seat=0.44, width=0.44):
    """A straight-backed chair."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_seat", (width, width, 0.06), (x, y, seat),
                  room.wood)
        room.part(f"{name}_back", (0.06, width, 0.52),
                  (x + width / 2.0 - 0.03, y, seat + 0.28), room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.08),
                 y + dy * (width - 0.08), 0.05, seat, room.wood)


def jar(room, name, at, *, height=0.46, radius=0.19, sides=8, mat=None):
    """An unglazed jar (*pote*). Radial, so it breaks up an interior of
    boxes."""
    profile = ((0.55, 0.0), (1.0, 0.28 * height), (0.86, 0.62 * height),
               (0.48, 0.9 * height), (0.58, height))
    with room.piece(name):
        obj = _revolved(room, name, at, (radius, radius), profile,
                        mat=mat or room.terracotta, sides=sides)
    return obj


def shelf(room, name, *, y, z, length=1.3, depth=0.26):
    """A shelf against the back wall, with its brackets."""
    x = room.back_x - depth / 2.0
    with room.piece(name):
        room.part(f"{name}_board", (depth, length, 0.05), (x, y, z), room.wood)
        for index, offset in enumerate((-length * 0.36, length * 0.36)):
            room.part(f"{name}_bracket_{index}", (depth * 0.7, 0.05, 0.16),
                      (x + 0.03, y + offset, z - 0.1), room.iron)


def lantern(room, name, *, y, z=2.1, energy=13.0):
    """A wrought-iron wall lantern, and the light it actually casts.

    The light is a separate object by necessity -- a lamp cannot be joined
    into a mesh -- so it stays a sibling of the joined lantern body.
    """
    x = room.back_x - 0.16
    with room.piece(name):
        room.part(f"{name}_bracket", (0.22, 0.05, 0.05),
                  (x + 0.08, y, z + 0.18), room.iron)
        room.part(f"{name}_cage", (0.16, 0.16, 0.22), (x, y, z), room.iron)
        room.part(f"{name}_flame", (0.09, 0.09, 0.13), (x, y, z),
                  room.lamplight)
    return room.light(f"{name}_light", "POINT", (x - 0.05, y, z),
                      (0.0, 0.0, -1.0), energy, (1.0, 0.82, 0.55), radius=0.14)


def barrel(room, name, at, *, radius=0.32, height=0.76):
    """A staved storage barrel with iron reinforcement hoops."""
    x, y = at
    profile = ((0.86, 0.0), (1.08, 0.5 * height), (0.86, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.wood,
                  sides=10)
        for index, level in enumerate((0.18, 0.50, 0.82)):
            room.part(f"{name}_hoop_{index}", (radius * 2.22, radius * 2.22,
                                               0.04),
                      (x, y, height * level), room.iron)


def sack(room, name, at, *, width=0.46, depth=0.42, height=0.58, rotation=0.0):
    """A burlap sack of flour or grain, gathered and tied at the neck."""
    x, y = at
    profile = ((0.75, 0.0), (1.05, 0.32 * height), (0.98, 0.65 * height),
               (0.65, 0.88 * height), (0.72, height))
    with room.piece(name):
        _revolved(room, name, at, (depth / 2.0, width / 2.0), profile,
                  mat=room.cloth, rotation=rotation)
        room.part(f"{name}_tie", (depth * 0.72, width * 0.72, 0.04),
                  (x, y, height * 0.88), room.straw)


def sack_stack(room, name, at, count=3):
    """A leaning cluster of sacks. One piece, not three."""
    x, y = at
    offsets = ((0.0, 0.0, 0.0), (0.22, 0.35, 0.25), (-0.20, -0.32, -0.35))
    with room.piece(name):
        for index in range(min(count, len(offsets))):
            dx, dy, rot = offsets[index]
            sack(room, f"{name}_{index}", (x + dx, y + dy), rotation=rot)


# ---------------------------------------------------------------------------
# The wall itself
# ---------------------------------------------------------------------------

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

    with room.piece("azulejo_dado"):
        for index, (a, b) in enumerate(spans):
            if b - a < 0.05:
                continue
            room.part(f"azulejo_dado_{index}", (proud, b - a, height),
                      (x, (a + b) / 2.0, height / 2.0), room.azulejo)
            room.part(f"azulejo_rail_{index}", (proud + 0.04, b - a, 0.06),
                      (x - 0.01, (a + b) / 2.0, height + 0.03), room.wood)


def window_dressing(room, name, y0, y1, z0, z1, *, grille=True, shutters=True):
    """An iron grille over the opening, and shutters folded back beside it."""
    x = room.back_x - 0.04
    cy = (y0 + y1) / 2.0
    with room.piece(name):
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
                room.part(f"{name}_shutter_{index}",
                          (0.05, span * 0.34, z1 - z0),
                          (x - 0.1, cy + side * (span * 0.5 + span * 0.17),
                           (z0 + z1) / 2.0), room.wood)


def stair(room, name, *, y, x_start, steps=7, rise=0.19, run=0.3, width=1.5,
          direction=-1.0):
    """A flight of steps going DOWN, away from the floor plane.

    The way out of a storey. `direction` is the axis the flight travels:
    -1 steps toward the camera, +1 steps away from it. At this camera a flight
    running toward the viewer disappears under the status menu almost at once,
    so a visible stair down normally runs AWAY, through an opening.
    """
    with room.piece(name):
        for index in range(steps):
            top = -rise * index
            x = x_start + direction * run * index
            room.part(f"{name}_tread_{index}", (run, width, rise + 0.02),
                      (x, y, top - (rise + 0.02) / 2.0), room.wood)
    return x_start + direction * run * (steps - 1), -rise * (steps - 1)


# ---------------------------------------------------------------------------
# Shop and bakery
# ---------------------------------------------------------------------------

def counter(room, name, at, *, length=1.8, width=0.68, height=0.88, panels=3):
    """A merchant shop counter (*balcao*): heavy dark timber carcass, recessed
    front panelling, overhanging top slab and a plinth."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_carcass",
                  (width * 0.88, length * 0.94, height * 0.88),
                  (x, y, height * 0.44), room.wood)
        room.part(f"{name}_top", (width, length, 0.08),
                  (x, y, height + 0.04), room.wood)
        room.part(f"{name}_plinth", (width * 0.92, length * 0.96, 0.10),
                  (x, y, 0.05), room.wood)
        # Panels face -X, toward the customer and the camera.
        panel_w = (length * 0.8) / panels
        front_x = x - (width * 0.88) / 2.0 - 0.015
        for index in range(panels):
            py = y - (length * 0.8) / 2.0 + panel_w * (index + 0.5)
            room.part(f"{name}_panel_{index}",
                      (0.03, panel_w * 0.82, height * 0.58),
                      (front_x, py, height * 0.52), room.wood)


def bread_oven(room, name, at, *, length=1.5, depth=1.3, height=1.6):
    """A masonry wood-fired bread oven (*forno a lenha*).

    Thick stone base with a firewood niche under it, a clay baking vault over
    that, an open mouth showing the ember bed, and a terracotta flue. The
    embers are emissive and want a `room.light` beside them.
    """
    x, y = at
    base_h = 0.72
    with room.piece(name):
        room.part(f"{name}_base", (depth, length, base_h),
                  (x, y, base_h / 2.0), room.stone)
        room.part(f"{name}_log_niche",
                  (depth * 0.7, length * 0.5, base_h * 0.65),
                  (x - depth * 0.16, y, base_h * 0.35), room.whitewash)
        for index, offset in enumerate((-0.18, 0.0, 0.18)):
            room.part(f"{name}_fuel_log_{index}", (depth * 0.55, 0.12, 0.10),
                      (x - depth * 0.15, y + offset, 0.08), room.wood)

        dome_h = height - base_h
        room.part(f"{name}_dome", (depth * 0.92, length * 0.92, dome_h),
                  (x, y, base_h + dome_h / 2.0), room.terracotta)

        mouth_w = length * 0.44
        mouth_h = dome_h * 0.62
        mouth_x = x - (depth * 0.92) / 2.0 - 0.02
        room.part(f"{name}_mouth_frame",
                  (0.08, mouth_w + 0.16, mouth_h + 0.14),
                  (mouth_x + 0.02, y, base_h + mouth_h / 2.0 + 0.08),
                  room.stone)
        room.part(f"{name}_embers", (0.35, mouth_w * 0.85, 0.12),
                  (mouth_x + 0.22, y, base_h + 0.06), room.embers)

        chimney_h = 1.6
        room.part(f"{name}_chimney", (0.32, 0.32, chimney_h),
                  (x + depth * 0.25, y, height + chimney_h / 2.0),
                  room.terracotta)


def bread_basket(room, name, at, *, radius=0.22, height=0.14, loaves=None):
    """A woven basket of crusty loaves (*broas*)."""
    x, y = at
    profile = ((0.80, 0.0), (1.05, 0.5 * height), (1.18, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.straw)
        loaf_mat = loaves or room.bread
        for index, (dx, dy, size, lift) in enumerate((
                (-0.06, -0.05, 0.16, 0.04),
                (0.07, 0.04, 0.15, 0.03),
                (-0.02, 0.08, 0.14, 0.05))):
            room.part(f"{name}_loaf_{index}", (size, size, size * 0.68),
                      (x + dx, y + dy, height + lift), loaf_mat)


def peel(room, name, at, *, length=1.75, angle_deg=14.0):
    """A baker's peel (*pa de forno*), leaning against the wall or the oven."""
    x, y = at
    rad = math.radians(angle_deg)
    with room.piece(name):
        room.part(f"{name}_handle", (0.05, 0.05, length),
                  (x + math.sin(rad) * length * 0.45, y,
                   math.cos(rad) * length * 0.5),
                  room.wood, rotation=(0.0, rad, 0.0))
        room.part(f"{name}_blade", (0.34, 0.28, 0.03), (x, y, 0.16), room.wood)


def demijohn(room, name, at, *, height=0.52, radius=0.18):
    """A wicker-cased glass demijohn (*garrafao*) for oil or wine."""
    x, y = at
    profile = ((0.65, 0.0), (1.1, 0.35 * height), (0.95, 0.75 * height),
               (0.35, 0.88 * height), (0.38, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.straw)
        room.part(f"{name}_cork", (0.09, 0.09, 0.08), (x, y, height + 0.03),
                  room.wood)


def scales(room, name, at, *, height=0.42, width=0.38):
    """A tabletop balance (*balanca*) for weighing dry goods and coin."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_base", (0.16, 0.16, 0.04), (x, y, 0.02), room.iron)
        room.part(f"{name}_pillar", (0.04, 0.04, height), (x, y, height / 2.0),
                  room.iron)
        room.part(f"{name}_beam", (0.03, width, 0.03), (x, y, height - 0.02),
                  room.bronze)
        for index, side in enumerate((-1.0, 1.0)):
            pan_y = y + side * (width / 2.0 - 0.04)
            room.part(f"{name}_string_{index}", (0.015, 0.015, height * 0.45),
                      (x, pan_y, height * 0.65), room.iron)
            room.part(f"{name}_pan_{index}", (0.12, 0.12, 0.02),
                      (x, pan_y, height * 0.42), room.bronze)


# ---------------------------------------------------------------------------
# Forge
# ---------------------------------------------------------------------------

def forge(room, name, at, *, length=1.8, depth=1.1, height=0.86,
          chimney_h=2.3):
    """A masonry forge hearth (*forja*): stone body, a charcoal bed with
    incandescent coke, an iron hood and a flue.

    The ember bed is emissive but casts nothing on its own -- give it a
    `room.light` so the shadows in the room come from the fire that motivates
    them.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_masonry", (depth, length, height),
                  (x, y, height / 2.0), room.stone)
        room.part(f"{name}_rim_front", (0.14, length + 0.06, 0.10),
                  (x - depth / 2.0 + 0.07, y, height + 0.05), room.stone)
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_rim_side{index}", (depth, 0.14, 0.10),
                      (x, y + side * (length / 2.0 - 0.07), height + 0.05),
                      room.stone)

        room.part(f"{name}_charcoal", (depth * 0.78, length * 0.72, 0.10),
                  (x + 0.05, y, height + 0.02), room.charcoal)
        room.part(f"{name}_embers", (depth * 0.72, length * 0.65, 0.14),
                  (x + 0.05, y, height + 0.04), room.embers)

        hood_z = height + 1.1
        room.part(f"{name}_hood", (depth * 0.85, length * 0.85, 0.55),
                  (x + 0.05, y, hood_z), room.iron)
        room.part(f"{name}_chimney", (0.42, 0.42, chimney_h),
                  (x + depth * 0.22, y, hood_z + chimney_h / 2.0 + 0.25),
                  room.stone)


def anvil(room, name, at, *, horn_len=0.78, width=0.26, height=0.44,
          stump_h=0.46):
    """An anvil (*bigorna*) on a banded hardwood stump (*cepo*)."""
    x, y = at
    stump_dia = max(width * 1.8, 0.48)
    with room.piece(name):
        room.part(f"{name}_stump", (stump_dia, stump_dia, stump_h),
                  (x, y, stump_h / 2.0), room.wood)
        room.part(f"{name}_stump_band",
                  (stump_dia + 0.04, stump_dia + 0.04, 0.06),
                  (x, y, stump_h * 0.75), room.iron)

        az = stump_h
        room.part(f"{name}_foot", (width * 1.15, horn_len * 0.62, 0.08),
                  (x, y, az + 0.04), room.forge_scale)
        room.part(f"{name}_waist",
                  (width * 0.65, horn_len * 0.42, height * 0.45),
                  (x, y, az + 0.08 + height * 0.225), room.forge_scale)
        room.part(f"{name}_table", (width, horn_len * 0.65, height * 0.42),
                  (x, y + horn_len * 0.08, az + height * 0.78), room.iron)
        room.part(f"{name}_horn",
                  (width * 0.68, horn_len * 0.38, height * 0.32),
                  (x, y - horn_len * 0.38, az + height * 0.78), room.iron)


def quench_tub(room, name, at, *, radius=0.32, height=0.56):
    """A staved slack tub (*tina de tempera*) with iron hoops, standing full."""
    x, y = at
    profile = ((0.90, 0.0), (1.08, 0.5 * height), (1.14, height))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius), profile, mat=room.wood,
                  sides=10)
        for index, level in enumerate((0.25, 0.82)):
            room.part(f"{name}_hoop_{index}", (radius * 2.3, radius * 2.3,
                                               0.04),
                      (x, y, height * level), room.iron)
        room.part(f"{name}_water", (radius * 1.9, radius * 1.9, 0.02),
                  (x, y, height * 0.90), room.iron)


def bellows(room, name, at, *, length=1.1, width=0.52, height=0.38):
    """Leather and hardwood bellows (*fole*), nozzle pointing into the forge."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_board_bot", (length * 0.85, width, 0.05),
                  (x, y, 0.08), room.wood)
        room.part(f"{name}_board_top", (length * 0.85, width, 0.05),
                  (x, y, height), room.wood)
        room.part(f"{name}_leather",
                  (length * 0.78, width * 0.92, height - 0.12),
                  (x, y, height / 2.0 + 0.02), room.cloth)
        room.part(f"{name}_pipe", (length * 0.45, 0.08, 0.08),
                  (x - length * 0.55, y, 0.18), room.iron)
        room.part(f"{name}_handle", (0.55, 0.06, 0.06),
                  (x + length * 0.55, y, height + 0.08), room.wood)


def weapon_rack(room, name, at, *, length=1.65, depth=0.45, height=1.75):
    """A display rack of forged blades, with a shield blank leaning on it."""
    x, y = at
    with room.piece(name):
        for index, side in enumerate((-1.0, 1.0)):
            py = y + side * (length / 2.0 - 0.06)
            room.part(f"{name}_post_{index}", (0.09, 0.09, height),
                      (x, py, height / 2.0), room.wood)
            room.part(f"{name}_foot_{index}", (depth, 0.09, 0.08),
                      (x, py, 0.04), room.wood)
        for index, level in enumerate((height * 0.35, height * 0.85)):
            room.part(f"{name}_rail_{index}", (0.06, length, 0.08),
                      (x, y, level), room.wood)

        for index, offset in enumerate((-0.45, -0.15, 0.15)):
            sy = y + offset
            room.part(f"{name}_blade_{index}", (0.03, 0.07, 0.95),
                      (x - 0.04, sy, height * 0.58), room.iron)
            room.part(f"{name}_guard_{index}", (0.05, 0.22, 0.04),
                      (x - 0.04, sy, height * 0.58 + 0.48), room.iron)
            room.part(f"{name}_grip_{index}", (0.03, 0.03, 0.20),
                      (x - 0.04, sy, height * 0.58 + 0.60), room.wood)

        room.part(f"{name}_shield", (0.05, 0.48, 0.65),
                  (x - 0.08, y + length / 2.0 - 0.22, height * 0.42),
                  room.wood, rotation=(0.0, 0.12, 0.0))
        room.part(f"{name}_shield_boss", (0.09, 0.12, 0.12),
                  (x - 0.12, y + length / 2.0 - 0.22, height * 0.42),
                  room.iron)


def tool_rail(room, name, *, y, z, length=1.3):
    """A wall batten hung with tongs and hammers."""
    x = room.back_x - 0.06
    with room.piece(name):
        room.part(f"{name}_batten", (0.04, length, 0.10), (x, y, z), room.wood)
        for index, offset in enumerate((-0.42, -0.14, 0.14, 0.42)):
            ty = y + offset
            room.part(f"{name}_peg_{index}", (0.16, 0.02, 0.02),
                      (x - 0.08, ty, z), room.iron)
            if index % 2 == 0:
                room.part(f"{name}_hammer_handle_{index}", (0.03, 0.03, 0.45),
                          (x - 0.12, ty, z - 0.24), room.wood)
                room.part(f"{name}_hammer_head_{index}", (0.08, 0.14, 0.06),
                          (x - 0.12, ty, z - 0.45), room.iron)
            else:
                room.part(f"{name}_tongs_{index}", (0.04, 0.06, 0.55),
                          (x - 0.12, ty, z - 0.28), room.iron)


def ingot_stack(room, name, at, rows=3, cols=2):
    """A stack of cast iron and bronze ingots."""
    x, y = at
    ingot_l, ingot_w, ingot_h = 0.32, 0.14, 0.07
    with room.piece(name):
        for row in range(rows):
            for col in range(cols):
                ix = x + (col - cols / 2.0 + 0.5) * (ingot_w + 0.02)
                iy = y + (row % 2) * 0.04
                mat = room.bronze if (row + col) % 3 == 0 else room.iron
                room.part(f"{name}_ingot_{row}_{col}",
                          (ingot_w, ingot_l, ingot_h),
                          (ix, iy, row * ingot_h + ingot_h / 2.0), mat)


def workbench(room, name, at, *, length=1.65, width=0.68, height=0.86):
    """A smith's workbench with a bench vice and a tool shelf under it."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.09), (x, y, height),
                  room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.16),
                 y + dy * (length - 0.16), 0.10, height - 0.045, room.wood)
        room.part(f"{name}_shelf", (width - 0.16, length - 0.16, 0.04),
                  (x, y, 0.22), room.wood)
        room.part(f"{name}_vice_base", (0.16, 0.16, 0.10),
                  (x - width / 2.0 + 0.08, y - length / 2.0 + 0.12,
                   height + 0.09), room.iron)
        room.part(f"{name}_vice_jaw", (0.08, 0.18, 0.12),
                  (x - width / 2.0 + 0.04, y - length / 2.0 + 0.12,
                   height + 0.18), room.iron)


def mercantile_shelf(room, name, at, *, length=1.45, depth=0.38, height=1.75,
                     tiers=3):
    """A freestanding merchant display shelf (*estante de mercearia*).

    Heavy dark timber uprights, back rail, three shelves loaded with dry-goods
    crocks, unglazed earthenware jars, and small storage tins.
    """
    x, y = at
    with room.piece(name):
        # Upright frames at both ends
        for index, side in enumerate((-1.0, 1.0)):
            sy = y + side * (length / 2.0 - 0.05)
            room.part(f"{name}_post_front_{index}", (0.07, 0.07, height),
                      (x - depth / 2.0 + 0.035, sy, height / 2.0), room.wood)
            room.part(f"{name}_post_back_{index}", (0.07, 0.07, height),
                      (x + depth / 2.0 - 0.035, sy, height / 2.0), room.wood)
            room.part(f"{name}_brace_top_{index}", (depth - 0.07, 0.05, 0.06),
                      (x, sy, height - 0.03), room.wood)
            room.part(f"{name}_brace_bot_{index}", (depth - 0.07, 0.05, 0.06),
                      (x, sy, 0.12), room.wood)

        # Back slat braces
        room.part(f"{name}_back_rail_0", (0.03, length, 0.08),
                  (x + depth / 2.0 - 0.015, y, height * 0.45), room.wood)
        room.part(f"{name}_back_rail_1", (0.03, length, 0.08),
                  (x + depth / 2.0 - 0.015, y, height * 0.82), room.wood)

        # Shelves and wares
        shelf_spacing = (height - 0.35) / tiers
        for tier in range(tiers):
            sz = 0.28 + tier * shelf_spacing
            room.part(f"{name}_board_{tier}", (depth, length, 0.04),
                      (x, y, sz), room.wood)

            # Populated dry wares on each shelf
            if tier == 0:
                # Lower tier: heavy jars and crocks
                for j_idx, offset in enumerate((-0.42, -0.14, 0.14, 0.42)):
                    mat = room.terracotta if j_idx % 2 == 0 else room.crock
                    _revolved(room, f"{name}_t0_jar_{j_idx}", (x, y + offset),
                              (0.12, 0.12),
                              ((0.7, 0.0), (1.0, 0.14), (0.85, 0.26), (0.6, 0.32)),
                              mat=mat, sides=8)
            elif tier == 1:
                # Mid tier: smaller pots, canisters, and tea/spice boxes
                for b_idx, offset in enumerate((-0.45, -0.18, 0.12, 0.40)):
                    if b_idx % 2 == 0:
                        room.part(f"{name}_t1_tin_{b_idx}", (0.16, 0.16, 0.22),
                                  (x, y + offset, sz + 0.13), room.bronze)
                    else:
                        _revolved(room, f"{name}_t1_pot_{b_idx}", (x, y + offset),
                                  (0.09, 0.09),
                                  ((0.8, 0.0), (1.1, 0.10), (0.7, 0.20)),
                                  mat=room.terracotta, sides=8)
            else:
                # Top tier: small flasks and stacked wooden bowls
                for s_idx, offset in enumerate((-0.38, 0.0, 0.38)):
                    room.part(f"{name}_t2_flask_{s_idx}", (0.10, 0.10, 0.18),
                              (x, y + offset, sz + 0.11), room.crock)


def apothecary_rack(room, name, *, y, z=2.05, length=1.1, depth=0.22):
    """A wall-hung apothecary and summoner supply rack.

    Fitted with small cubby slots holding ceramic potion vials, distilled
    water flasks, and dried herb packets.
    """
    x = room.back_x - depth / 2.0
    height = 0.65
    with room.piece(name):
        room.part(f"{name}_frame_top", (depth, length, 0.035),
                  (x, y, z + height / 2.0), room.wood)
        room.part(f"{name}_frame_bot", (depth, length, 0.035),
                  (x, y, z - height / 2.0), room.wood)
        for side, sy in ((0, y - length / 2.0 + 0.02), (1, y + length / 2.0 - 0.02)):
            room.part(f"{name}_side_{side}", (depth, 0.035, height),
                      (x, sy, z), room.wood)

        # Mid shelf
        room.part(f"{name}_shelf_mid", (depth - 0.02, length - 0.05, 0.03),
                  (x, y, z), room.wood)

        # Small cubby dividers
        for d_idx, dy in enumerate((-length * 0.22, length * 0.22)):
            room.part(f"{name}_div_{d_idx}", (depth - 0.03, 0.025, height - 0.07),
                      (x, y + dy, z), room.wood)

        # Potion flasks and herbal vials
        for v_idx, offset in enumerate((-0.38, -0.12, 0.12, 0.38)):
            mat = room.crock if v_idx % 2 == 0 else room.bronze
            room.part(f"{name}_vial_{v_idx}", (0.07, 0.07, 0.16),
                      (x - 0.02, y + offset, z - height / 4.0 + 0.08), mat)
            room.part(f"{name}_tincture_{v_idx}", (0.06, 0.06, 0.14),
                      (x - 0.02, y + offset, z + height / 4.0 + 0.07), room.terracotta)


def hanging_rack(room, name, at, *, length=1.4, height=2.45):
    """A ceiling-hung timber rail with iron hooks, carrying dried herbs,
    cured sausages, and garlic braids."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_beam", (0.08, length, 0.08),
                  (x, y, height), room.wood)
        # Hanger rods to ceiling
        for side, sy in ((0, y - length * 0.4), (1, y + length * 0.4)):
            room.part(f"{name}_rod_{side}", (0.02, 0.02, room.ceiling_z - height),
                      (x, sy, height + (room.ceiling_z - height) / 2.0), room.iron)

        # Hanging hooks and provisions
        for h_idx, offset in enumerate((-0.45, -0.15, 0.15, 0.45)):
            hy = y + offset
            room.part(f"{name}_hook_{h_idx}", (0.02, 0.02, 0.08),
                      (x, hy, height - 0.04), room.iron)
            if h_idx % 2 == 0:
                # Garlic braid / herb bundle
                _revolved(room, f"{name}_herb_{h_idx}", (x, hy),
                          (0.06, 0.06),
                          ((0.4, 0.0), (1.1, -0.15), (0.7, -0.32)),
                          mat=room.straw, sides=6)
            else:
                # Cured sausage / dried provision
                room.part(f"{name}_sausage_{h_idx}", (0.06, 0.06, 0.28),
                          (x, hy, height - 0.20), room.cloth)


def grain_bin(room, name, at, *, length=0.92, width=0.58, height=0.64):
    """A slatted wooden flour and grain chest (*arca de farinha*).

    Has an angled hinged lid propped open, a flour scoop inside, and a dusting
    of white flour along the rim.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_body", (width, length, height * 0.78),
                  (x, y, height * 0.39), room.wood)
        room.part(f"{name}_plinth", (width + 0.04, length + 0.04, 0.06),
                  (x, y, 0.03), room.wood)
        # Angled lid
        room.part(f"{name}_lid", (width * 0.95, length + 0.02, 0.04),
                  (x + width * 0.12, y, height * 0.92), room.wood,
                  rotation=(0.0, -0.22, 0.0))
        # Flour bed inside
        room.part(f"{name}_flour", (width * 0.82, length * 0.86, 0.15),
                  (x, y, height * 0.58), room.whitewash)
        # Wooden flour scoop (*pa de farinha*)
        room.part(f"{name}_scoop", (0.24, 0.12, 0.08),
                  (x - 0.06, y + 0.14, height * 0.68), room.wood,
                  rotation=(0.0, 0.35, 0.25))


def counter_dressing(room, name, at, *, length=0.65, width=0.45):
    """Tabletop dressing for Alicia's counter:
    - The merchant ledger book with open pages,
    - An iron inkpot with quill,
    - Laura's lunch bundle (bread, cheese, pear tied in a clean cloth).
    """
    x, y = at
    with room.piece(name):
        # Open ledger book
        room.part(f"{name}_ledger_cover", (0.28, 0.38, 0.02),
                  (x, y - 0.14, 0.01), room.wood)
        room.part(f"{name}_ledger_pages", (0.26, 0.35, 0.03),
                  (x, y - 0.14, 0.025), room.whitewash)

        # Inkpot and quill
        room.part(f"{name}_inkpot", (0.07, 0.07, 0.08),
                  (x + 0.10, y + 0.02, 0.04), room.iron)
        room.part(f"{name}_quill", (0.02, 0.02, 0.20),
                  (x + 0.10, y + 0.02, 0.14), room.whitewash,
                  rotation=(0.15, -0.25, 0.0))

        # Laura's lunch bundle: warm bread, cheese, pear tied in neat cloth with knot
        _revolved(room, f"{name}_lunch_cloth", (x - 0.04, y + 0.16),
                  (0.12, 0.14),
                  ((0.7, 0.0), (1.1, 0.08), (0.9, 0.16), (0.4, 0.22)),
                  mat=room.cloth, sides=8)
        room.part(f"{name}_lunch_knot", (0.06, 0.08, 0.05),
                  (x - 0.04, y + 0.16, 0.24), room.cloth)


def grindstone(room, name, at, *, wheel_dia=0.56, wheel_thick=0.12, height=0.78,
               length=0.82):
    """A smith's sharpening grindstone on a heavy timber trestle (*rebolo*).

    Heavy round stone wheel mounted on a forged iron axle, timber A-frame legs,
    a foot treadle bar, and a water drip trough.
    """
    x, y = at
    with room.piece(name):
        # Timber A-frame trestle
        for side, sy in ((0, y - length / 2.0 + 0.06), (1, y + length / 2.0 - 0.06)):
            _leg(room, f"{name}_leg_f_{side}", x - 0.22, sy, 0.08, height * 0.88, room.wood)
            _leg(room, f"{name}_leg_b_{side}", x + 0.22, sy, 0.08, height * 0.88, room.wood)
            room.part(f"{name}_cap_{side}", (0.52, 0.08, 0.08),
                      (x, sy, height * 0.88), room.wood)
            room.part(f"{name}_tie_{side}", (0.48, 0.06, 0.06),
                      (x, sy, 0.18), room.wood)

        # Cross rails
        room.part(f"{name}_rail_front", (0.06, length, 0.06),
                  (x - 0.20, y, 0.22), room.wood)
        room.part(f"{name}_rail_back", (0.06, length, 0.06),
                  (x + 0.20, y, 0.22), room.wood)

        # Stone wheel (revolved 10-sided cylinder)
        _revolved(room, f"{name}_stone_wheel", (x, y),
                  (wheel_dia / 2.0, wheel_dia / 2.0),
                  ((1.0, height - wheel_thick / 2.0), (1.0, height + wheel_thick / 2.0)),
                  mat=room.stone, sides=10, rotation=0.0)

        # Iron axle
        room.part(f"{name}_axle", (0.04, length + 0.12, 0.04),
                  (x, y, height), room.iron)

        # Water drip trough under stone
        room.part(f"{name}_trough", (wheel_dia * 0.72, length * 0.65, 0.14),
                  (x, y, height * 0.48), room.iron)


def fuel_bunker(room, name, at, *, length=0.95, width=0.68, height=0.52):
    """A heavy low charcoal hopper (*carvoeira*) with coal shovel.

    Holds charcoal fuel for the forge or bakery hearth.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_box", (width, length, height),
                  (x, y, height / 2.0), room.wood)
        room.part(f"{name}_charcoal_bed", (width * 0.86, length * 0.88, 0.18),
                  (x, y, height - 0.08), room.charcoal)
        # Heavy iron shovel leaning against the rim
        room.part(f"{name}_shovel_handle", (0.04, 0.04, 0.85),
                  (x - width / 2.0 - 0.08, y + 0.12, 0.48), room.wood,
                  rotation=(0.12, 0.28, 0.0))
        room.part(f"{name}_shovel_blade", (0.16, 0.18, 0.03),
                  (x - width / 2.0 - 0.16, y + 0.18, 0.10), room.iron,
                  rotation=(0.0, 0.28, 0.12))


def armor_stand(room, name, at, *, height=1.62, width=0.58):
    """A hardwood cross-buck armor display stand (*manequim de armadura*).

    Displays a forged iron cuirass / breastplate blank and pauldrons.
    """
    x, y = at
    with room.piece(name):
        # Timber cross stand
        room.part(f"{name}_base_x", (0.48, 0.09, 0.06), (x, y, 0.03), room.wood)
        room.part(f"{name}_base_y", (0.09, 0.48, 0.06), (x, y, 0.03), room.wood)
        room.part(f"{name}_mast", (0.09, 0.09, height),
                  (x, y, height / 2.0), room.wood)
        room.part(f"{name}_crosspiece", (0.08, width, 0.08),
                  (x, y, height * 0.88), room.wood)

        # Forged iron breastplate blank
        az = height * 0.62
        room.part(f"{name}_breastplate", (0.24, width * 0.72, height * 0.38),
                  (x - 0.03, y, az), room.forge_scale)
        room.part(f"{name}_neck_guard", (0.14, width * 0.42, 0.08),
                  (x - 0.04, y, az + height * 0.21), room.iron)
        for side, sy in ((0, y - width * 0.42), (1, y + width * 0.42)):
            room.part(f"{name}_pauldron_{side}", (0.18, 0.14, 0.12),
                      (x, sy, height * 0.86), room.iron)


def woodpile(room, name, at, *, length=1.15, width=0.52, height=0.72):
    """A neat stack of split firewood logs for baking or smithing."""
    x, y = at
    with room.piece(name):
        # Base cribbing rails
        for side, sy in ((0, y - length / 2.0 + 0.06), (1, y + length / 2.0 - 0.06)):
            room.part(f"{name}_base_{side}", (width, 0.08, 0.08),
                      (x, sy, 0.04), room.wood)
        # End stakes
        for side, sy in ((0, y - length / 2.0 + 0.04), (1, y + length / 2.0 - 0.04)):
            for end, ex in ((0, x - width / 2.0 + 0.04), (1, x + width / 2.0 - 0.04)):
                room.part(f"{name}_stake_{side}_{end}", (0.06, 0.06, height),
                          (ex, sy, height / 2.0), room.wood)

        # Tiered split logs
        log_dia = 0.12
        layers = int(height / (log_dia * 0.85))
        for layer in range(layers):
            lz = 0.08 + layer * (log_dia * 0.85) + log_dia / 2.0
            logs_in_layer = 3 if layer % 2 == 0 else 2
            for l_idx in range(logs_in_layer):
                offset_x = (l_idx - (logs_in_layer - 1) / 2.0) * (log_dia * 1.05)
                room.part(f"{name}_log_{layer}_{l_idx}", (log_dia * 0.95, length - 0.12, log_dia * 0.95),
                          (x + offset_x, y, lz), room.wood)


def dough_trough(room, name, at, *, length=1.45, width=0.62, height=0.82):
    """A traditional Portuguese baker's dough kneading trough (*masseira / artesa*).

    Deep flared timber trough on splayed legs, with a flour bed and dough scraper.
    """
    x, y = at
    with room.piece(name):
        # Splayed legs
        leg_h = height * 0.55
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5), (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.14),
                 y + dy * (length - 0.18), 0.08, leg_h, room.wood)
        # Stretcher rails
        room.part(f"{name}_stretcher", (width - 0.14, length - 0.18, 0.05),
                  (x, y, 0.18), room.wood)

        # Flared wooden trough body
        trough_h = height - leg_h
        trough_z = leg_h + trough_h / 2.0
        room.part(f"{name}_trough_bot", (width * 0.72, length * 0.85, 0.04),
                  (x, y, leg_h + 0.02), room.wood)
        room.part(f"{name}_side_front", (0.04, length, trough_h),
                  (x - width / 2.0 + 0.02, y, trough_z), room.wood)
        room.part(f"{name}_side_back", (0.04, length, trough_h),
                  (x + width / 2.0 - 0.02, y, trough_z), room.wood)
        room.part(f"{name}_end_l", (width - 0.08, 0.04, trough_h),
                  (x, y - length / 2.0 + 0.02, trough_z), room.wood)
        room.part(f"{name}_end_r", (width - 0.08, 0.04, trough_h),
                  (x, y + length / 2.0 - 0.02, trough_z), room.wood)

        # Flour dusting inside trough
        room.part(f"{name}_flour", (width * 0.65, length * 0.78, 0.06),
                  (x, y, leg_h + 0.06), room.whitewash)
        # Dough paddle / scraper
        room.part(f"{name}_paddle", (0.28, 0.16, 0.02),
                  (x - 0.05, y + 0.18, leg_h + 0.12), room.wood,
                  rotation=(0.0, 0.15, 0.22))


def storage_loft(room, name, at, *, length=3.4, depth=0.85, height=3.1):
    """An overhead timber mezzanine storage loft / bar rack for the forge."""
    x, y = at
    with room.piece(name):
        # Heavy support posts
        for side, sy in ((0, y - length / 2.0 + 0.1), (1, y + length / 2.0 - 0.1)):
            room.part(f"{name}_post_{side}", (0.12, 0.12, height),
                      (x - depth / 2.0 + 0.06, sy, height / 2.0), room.wood)
        # Main longitudinal bearer beam
        room.part(f"{name}_bearer", (0.12, length, 0.14),
                  (x - depth / 2.0 + 0.06, y, height - 0.07), room.wood)
        # Slatted loft deck
        room.part(f"{name}_deck", (depth, length, 0.05),
                  (x, y, height), room.wood)
        # Stored iron bar stock on loft
        for b_idx in range(4):
            by = y + (b_idx - 1.5) * 0.22
            room.part(f"{name}_stock_{b_idx}", (depth * 0.85, 0.06, 0.04),
                      (x, by, height + 0.05), room.iron)


