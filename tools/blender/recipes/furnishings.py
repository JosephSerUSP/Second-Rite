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


def _revolved(room, name, at, radii, profile, *, mat, sides=8, rotation=0.0,
              tilt=0.0):
    """A radial solid swept from a (scale, level) profile.

    Jars, sacks, barrels and tubs are all this shape with different numbers,
    and radial pieces are what stop an interior reading as a room of boxes.
    `radii` is (rx, ry) so a sack can be slightly oval without a scale on the
    object, which would fight the world-space box projection.

    `tilt` turns the swept axis away from vertical. At tilt=tau/4 the solid
    stands on its edge, which is the only way this vocabulary can make a WHEEL
    -- and a wheel is the one curve in it that reads in elevation rather than
    in plan.
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
    # room.lift is the surface this is standing on: the floor unless we are
    # inside an `Interior.surface` block. A radial piece parents directly
    # rather than going through `Interior.part`, so it has to add it itself.
    asset_core.parent_local(obj, room.root, loc=(x, y, room.lift),
                            rot=(tilt, 0.0, rotation))
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


def wax_bench(room, name, at, *, length=1.6, width=0.64, height=0.78):
    """The candle bench: a wax tray, a dipping frame, and finished lanterns.

    Alicia is scraping wax from a tray when the player finds her during the
    Vigil, and the lantern she hides behind the counter bears no human name.
    So the bakery is also where St. Maria's lanterns are made -- which is not a
    coincidence but an economy: the oven is already hot, and rendering wax
    wants exactly the heat that is otherwise going up the flue.

    Faces the camera: the tray and the taper row read from -X.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.07), (x, y, height),
                  room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.14),
                 y + dy * (length - 0.14), 0.08, height - 0.035, room.wood)

        # The tray, with the wax slab still in it and a scraper laid across.
        tray_y = y - length * 0.22
        room.part(f"{name}_tray", (width * 0.72, length * 0.42, 0.06),
                  (x, tray_y, height + 0.06), room.iron)
        room.part(f"{name}_wax_slab", (width * 0.6, length * 0.34, 0.05),
                  (x, tray_y, height + 0.08), room.straw)
        room.part(f"{name}_scraper_blade", (0.16, 0.05, 0.015),
                  (x - 0.06, tray_y + length * 0.2, height + 0.12), room.iron)
        room.part(f"{name}_scraper_grip", (0.05, 0.05, 0.14),
                  (x - 0.06, tray_y + length * 0.28, height + 0.13),
                  room.wood, rotation=(1.2, 0.0, 0.0))

        # The dipping frame: uprights, a crossbar, and the tapers hanging in
        # pairs off it. This is the piece's silhouette and it wants to be
        # legible against the whitewash, so the tapers hang clear of the top.
        frame_y = y + length * 0.24
        bar_z = height + 0.72
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_frame_post_{index}",
                      (0.06, 0.06, bar_z - height),
                      (x, frame_y + side * length * 0.2,
                       height + (bar_z - height) / 2.0), room.wood)
        room.part(f"{name}_frame_bar", (0.05, length * 0.46, 0.05),
                  (x, frame_y, bar_z), room.wood)
        for index in range(5):
            ty = frame_y - length * 0.18 + index * (length * 0.09)
            drop = 0.30 if index % 2 else 0.34
            room.part(f"{name}_taper_{index}", (0.035, 0.035, drop),
                      (x, ty, bar_z - 0.03 - drop / 2.0), room.straw)
            room.part(f"{name}_wick_{index}", (0.012, 0.012, 0.05),
                      (x, ty, bar_z - 0.03), room.charcoal)

        # Two finished lantern frames on the under-shelf, waiting for names.
        room.part(f"{name}_shelf", (width - 0.14, length - 0.14, 0.04),
                  (x, y, 0.24), room.wood)
        for index, offset in enumerate((-length * 0.22, length * 0.14)):
            ly = y + offset
            room.part(f"{name}_lantern_body_{index}", (0.16, 0.16, 0.22),
                      (x, ly, 0.37), room.iron)
            room.part(f"{name}_lantern_top_{index}", (0.20, 0.20, 0.04),
                      (x, ly, 0.50), room.iron)


def cloth_bundle(room, name, at, *, radius=0.17, height=0.24, rotation=0.0):
    """Goods tied into a cloth, ready to be carried (*embrulho*).

    Alicia ties bread, cheese and a bruised pear into a cloth for Laura, and
    the cloth comes back folded into a perfect square. A shop where everything
    is still on a shelf has not sold anything yet; a bundle is a transaction
    that has already happened.
    """
    x, y = at
    profile = ((0.55, 0.0), (1.0, height * 0.34), (0.82, height * 0.72),
               (0.30, height * 0.92))
    with room.piece(name):
        _revolved(room, name, at, (radius, radius * 0.92), profile,
                  mat=room.cloth, sides=8, rotation=rotation)
        room.part(f"{name}_knot", (radius * 0.7, radius * 0.7, height * 0.22),
                  (x, y, height * 0.98), room.cloth,
                  rotation=(0.0, 0.0, rotation + 0.5))
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_corner_{index}",
                      (radius * 0.34, radius * 0.34, height * 0.30),
                      (x + side * radius * 0.30, y + side * radius * 0.22,
                       height * 1.06), room.cloth,
                      rotation=(0.0, side * 0.6, rotation))


def stock_shelf(room, name, at, *, length=1.9, depth=0.42, height=2.05,
                tiers=4):
    """An open stock rack, loaded to the top (*prateleira*).

    "Watching people leave with full bags... it means they might come back."
    A shop reads as a shop because of VOLUME, not because of three
    representative props, and a rack is the cheapest volume in this
    vocabulary. Stock is graded by tier the way a real shop grades it: heavy
    and dull below, small and valuable at eye level, overflow above the reach.
    """
    x, y = at
    with room.piece(name):
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_upright_{index}", (depth, 0.08, height),
                      (x, y + side * (length / 2.0 - 0.04), height / 2.0),
                      room.wood)
        room.part(f"{name}_back", (0.04, length, height),
                  (x + depth / 2.0 - 0.02, y, height / 2.0), room.wood)

        for tier in range(tiers):
            z = 0.30 + tier * (height - 0.42) / max(tiers - 1, 1)
            room.part(f"{name}_board_{tier}", (depth, length, 0.05),
                      (x, y, z), room.wood)
            # Deterministic, and deliberately not uniform: a shelf of evenly
            # spaced identical boxes reads as a texture, not as stock.
            slots = 5 if tier % 2 else 4
            for slot in range(slots):
                sy = y - length * 0.40 + slot * (length * 0.80
                                                 / max(slots - 1, 1))
                phase = (tier * 7 + slot * 3) % 5
                with room.surface(z + 0.025):
                    if tier == 0:
                        if slot % 2 == 0:
                            sack(room, f"{name}_sack_{tier}_{slot}", (x, sy),
                                 width=0.30, depth=0.26, height=0.34,
                                 rotation=0.2 * phase)
                        else:
                            room.part(f"{name}_crate_{tier}_{slot}",
                                      (depth * 0.7, 0.30, 0.26),
                                      (x, sy, 0.13), room.wood)
                    elif tier == tiers - 1:
                        room.part(f"{name}_stack_{tier}_{slot}",
                                  (depth * 0.62, 0.24, 0.16 + 0.03 * phase),
                                  (x, sy, 0.08 + 0.015 * phase), room.cloth)
                    elif phase % 2:
                        jar(room, f"{name}_jar_{tier}_{slot}", (x, sy),
                            height=0.20 + 0.03 * (phase % 3), radius=0.085,
                            mat=room.crock)
                    else:
                        room.part(f"{name}_tin_{tier}_{slot}",
                                  (0.16, 0.15, 0.19), (x, sy, 0.095),
                                  room.bronze)


def water_stand(room, name, at, *, height=0.72, radius=0.30):
    """A water crock on a stand, with a dipper and a cup (*talha de agua*).

    "Please drink water before you descend. People return looking like they
    forgot they have bodies." It is the first thing Alicia says to the player
    and the only free thing in the shop, so it stands where a customer can
    reach it rather than behind the counter.
    """
    x, y = at
    profile = ((0.42, 0.0), (0.95, radius * 0.9), (1.0, radius * 1.9),
               (0.72, radius * 2.5), (0.52, radius * 2.7))
    with room.piece(name):
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * 0.34, y + dy * 0.34,
                 0.07, height, room.wood)
        room.part(f"{name}_top", (0.52, 0.52, 0.06), (x, y, height + 0.03),
                  room.wood)
        with room.surface(height + 0.06):
            _revolved(room, f"{name}_crock", (x, y), (radius, radius), profile,
                      mat=room.crock, sides=10)
        # The dipper hangs off the rim by its handle, which is what says the
        # water is for drinking rather than for the dough.
        room.part(f"{name}_dipper_bowl", (0.13, 0.13, 0.07),
                  (x - radius * 0.9, y, height + 0.52), room.crock)
        room.part(f"{name}_dipper_handle", (0.04, 0.04, 0.26),
                  (x - radius * 0.9, y, height + 0.66), room.wood,
                  rotation=(0.0, 0.35, 0.0))
        room.part(f"{name}_cup", (0.10, 0.10, 0.09),
                  (x + 0.06, y + 0.30, height + 0.11), room.crock)


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

        # The fire has to be seen from a LEVEL lens 18 metres away. A flat
        # ember bed lying on top of the hearth is a horizontal plane viewed
        # edge-on from there: it lights the room and is itself invisible, so
        # the forge read as a warm patch on a wall with no fire in it. The
        # coals are therefore heaped PROUD of the rim, and carry a front face
        # square to the camera. This is also what a working fire looks like --
        # coke is banked into a mound over the tuyere, not raked flat.
        mound_h = 0.30
        room.part(f"{name}_fire_bed", (depth * 0.62, length * 0.58, mound_h),
                  (x + 0.03, y, height + mound_h / 2.0), room.embers)
        room.part(f"{name}_fire_crown", (depth * 0.34, length * 0.32, 0.16),
                  (x + 0.03, y, height + mound_h + 0.05), room.embers)
        # Unburnt coke banked around the hot centre: the dark shoulder that
        # makes the bright core read as a CORE rather than as a glowing box.
        for index, (dx, dy) in enumerate(((-0.30, -0.34), (-0.30, 0.34),
                                          (0.26, -0.30), (0.26, 0.30))):
            room.part(f"{name}_coke_{index}",
                      (depth * 0.22, length * 0.22, 0.17),
                      (x + 0.03 + dx * depth * 0.5, y + dy * length * 0.5,
                       height + 0.09), room.charcoal,
                      rotation=(0.0, 0.0, 0.6 * index))

        # The hood, built as a taper rather than a slab. A single box hanging
        # over the fire reads as a black bar across the frame; a gathering
        # hood catches the firelight on its underside and its throat, which is
        # what puts the fire's own light back into the top of the picture.
        hood_z = height + 1.1
        room.part(f"{name}_hood_skirt", (depth * 0.98, length * 0.98, 0.10),
                  (x + 0.05, y, hood_z - 0.24), room.iron)
        room.part(f"{name}_hood", (depth * 0.85, length * 0.85, 0.44),
                  (x + 0.05, y, hood_z), room.iron)
        room.part(f"{name}_hood_throat", (depth * 0.52, length * 0.52, 0.26),
                  (x + 0.05, y, hood_z + 0.34), room.iron)
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


def scrap_heap(room, name, at, *, spread=0.9, layers=7):
    """Salvage waiting to be decided about: flattened lantern frames, and
    whatever the Labyrinth failed to digest.

    "She is hammering old lantern frames flat for reuse." Laura's stock is not
    bought, it is recovered, and this is the only disorder her room is allowed
    -- everything else she has already made a decision about. Flat plates lying
    at angles read as a heap at this camera where a mound of boxes does not.
    """
    x, y = at
    with room.piece(name):
        for index in range(layers):
            phase = (index * 5) % 7
            dx = (phase - 3) * spread * 0.09
            dy = (((index * 3) % 5) - 2) * spread * 0.16
            plate = 0.34 + 0.05 * (phase % 3)
            room.part(f"{name}_plate_{index}", (plate, plate * 0.72, 0.025),
                      (x + dx, y + dy, 0.02 + index * 0.022),
                      room.forge_scale if index % 3 else room.iron,
                      rotation=(0.0, 0.05 * (phase - 3), 0.42 * index))
        # Two frames not yet flattened, still recognisably lanterns.
        for index, (dx, dy, rot) in enumerate(((-0.28, 0.34, 0.5),
                                               (0.22, -0.38, -0.3))):
            room.part(f"{name}_frame_{index}", (0.17, 0.17, 0.24),
                      (x + dx, y + dy, 0.12), room.iron,
                      rotation=(0.35, 0.0, rot))
        room.part(f"{name}_bar", (0.06, 0.72, 0.04),
                  (x - spread * 0.34, y + 0.1, 0.03), room.iron,
                  rotation=(0.0, 0.0, 0.8))


def grindstone(room, name, at, *, radius=0.34, height=0.74, rotation=0.0):
    """A treadle grindstone in its frame, over a water trough (*mo de afiar*).

    The wheel is the only curve in this vocabulary that reads in ELEVATION
    rather than in plan -- every other radial piece is a jar seen end-on. Next
    to an anvil and a rack of straight bars that is worth a great deal, and it
    is also the fixture that says a smith SHARPENS as well as forges.
    """
    x, y = at
    axle_z = height + radius * 0.35
    with room.piece(name):
        for index, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_post_{index}", (0.10, 0.10, axle_z),
                      (x, y + side * (radius + 0.14), axle_z / 2.0), room.wood)
            room.part(f"{name}_foot_{index}", (0.62, 0.12, 0.09),
                      (x, y + side * (radius + 0.14), 0.045), room.wood)
        room.part(f"{name}_rail", (0.09, radius * 2 + 0.4, 0.09),
                  (x, y, axle_z), room.wood)

        # The wheel: a revolved disc stood on edge by the tilt.
        with room.surface(axle_z):
            _revolved(room, f"{name}_wheel", (x, y), (radius, radius),
                      ((0.30, -0.055), (0.95, -0.045), (1.0, 0.0),
                       (0.95, 0.045), (0.30, 0.055)),
                      mat=room.stone, sides=12, rotation=rotation,
                      tilt=math.tau / 4.0)
        room.part(f"{name}_axle", (0.06, radius * 2 + 0.3, 0.06),
                  (x, y, axle_z), room.iron)
        room.part(f"{name}_crank", (0.06, 0.06, 0.22),
                  (x, y + radius + 0.24, axle_z - 0.11), room.iron)
        room.part(f"{name}_crank_grip", (0.05, 0.14, 0.05),
                  (x, y + radius + 0.30, axle_z - 0.22), room.wood)

        # The trough the wheel dips into. A dry grindstone burns the temper
        # out of an edge, so a stone without water is a smith who does not
        # know her trade.
        room.part(f"{name}_trough", (0.42, radius * 1.7, 0.20),
                  (x, y, height - radius * 0.62), room.wood)
        room.part(f"{name}_water", (0.34, radius * 1.5, 0.02),
                  (x, y, height - radius * 0.56), room.iron)


def fine_bench(room, name, at, *, length=1.15, width=0.52, height=0.92):
    """The precious-metal bench: high, small, and slung with a catch skin.

    "The gold is pure... untouched." Laura takes goldwork as well as blade
    work, and the two are not done at the same bench -- fine work is done
    SITTING, high, close to the eye, over a leather skin that catches every
    filing worth sweeping up. Putting that beside the anvil is what stops the
    forge reading as one generic hammering station.
    """
    x, y = at
    with room.piece(name):
        room.part(f"{name}_top", (width, length, 0.07), (x, y, height),
                  room.wood)
        for index, (dx, dy) in enumerate(((0.5, -0.5), (0.5, 0.5),
                                          (-0.5, -0.5), (-0.5, 0.5))):
            _leg(room, f"{name}_leg_{index}", x + dx * (width - 0.12),
                 y + dy * (length - 0.12), 0.07, height - 0.035, room.wood)
        # The catch skin, sagging between the front rail and the bench.
        room.part(f"{name}_skin", (width * 0.86, length * 0.72, 0.03),
                  (x - width * 0.06, y, height - 0.30), room.cloth,
                  rotation=(0.0, 0.16, 0.0))
        room.part(f"{name}_skin_rail", (0.05, length * 0.72, 0.05),
                  (x - width / 2.0 - 0.06, y, height - 0.20), room.wood)

        # A pitch bowl on its ring, the peg the work is braced against, and a
        # row of small tools -- all small, because that is the whole point.
        room.part(f"{name}_peg", (0.20, 0.10, 0.06),
                  (x - width / 2.0 + 0.06, y - length * 0.24, height + 0.06),
                  room.wood)
        room.part(f"{name}_pitch_ring", (0.17, 0.17, 0.04),
                  (x, y + length * 0.16, height + 0.055), room.wood)
        room.part(f"{name}_pitch_bowl", (0.15, 0.15, 0.08),
                  (x, y + length * 0.16, height + 0.11), room.forge_scale)
        for index, offset in enumerate((-0.34, -0.26, -0.18)):
            room.part(f"{name}_tool_{index}", (0.03, 0.03, 0.20),
                      (x + width * 0.22, y + offset, height + 0.11),
                      room.iron, rotation=(0.0, 1.45, 0.0))
        room.part(f"{name}_box", (0.14, 0.20, 0.10),
                  (x + width * 0.18, y + length * 0.32, height + 0.09),
                  room.wood)
