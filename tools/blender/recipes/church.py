"""Masonry and liturgical vocabulary for a St. Maria church.

`interior.py` can only pierce a wall with rectangles, and a church is the one
building in the town whose openings are round-headed. These helpers close that
gap without changing the shell: the opening is still a rectangle whose top sits
at the arch APEX, and `arch_infill` fills the two spandrels (the wall above the
curve) with thin strips, so the opening reads as an arch from any angle. A ring
of voussoirs (`arch_ring`) then dresses the curve.

Walls are addressed the way `furnishings.door_frame` addresses them: `"back"`
is the far long wall (the lane's backdrop, spanning Y), `"-y"` / `"+y"` are the
end walls of a long hall (spanning X).

Pieces here are reusable; the church that uses them is declared in
`st_maria_church.py`.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import furnishings as furn  # noqa: E402


def _frame(room, wall, plane=None):
    """Return place(along, out, size_along, size_out, size_z, z, tilt=0).

    `out` is the offset from the wall plane toward the room's interior, so
    positive `out` is proud of the face. `plane` overrides the wall's plane
    (an alcove's back wall sits deeper than the room's).
    """
    if wall == "back":
        face = (room.back_x if plane is None else plane)

        def place(along, out, s_along, s_out, s_z, z, tilt=0.0):
            return {"size": (s_out, s_along, s_z),
                    "location": (face - out, along, z),
                    "rotation": (tilt, 0.0, 0.0)}
    else:
        sign = -1.0 if wall == "-y" else 1.0
        face = sign * (room.half_width if plane is None else plane)

        def place(along, out, s_along, s_out, s_z, z, tilt=0.0):
            return {"size": (s_along, s_out, s_z),
                    "location": (along, face - sign * out, z),
                    "rotation": (0.0, -tilt, 0.0)}
    return place


def _curve(half_span, rise, u):
    """Height above the springing line of a (segmental) arch at offset u."""
    r = half_span
    return rise * math.sqrt(max(0.0, 1.0 - (u / r) ** 2))


def arch_infill(room, name, wall, centre, half_span, spring_z, top_z, *,
                rise=None, strips=18, mat=None, plane=None, thick=None):
    """Fill the wall above an arch so a rectangular opening reads as round.

    The opening was pierced up to `top_z` (the apex, or higher); this puts wall
    back in over the spandrels. `rise` defaults to a semicircle.
    """
    mat = mat or room.whitewash
    rise = half_span if rise is None else rise
    thick = room.wall_thick if thick is None else thick
    place = _frame(room, wall, plane)
    width = 2.0 * half_span / strips
    with room.piece(name):
        for k in range(strips):
            u = -half_span + (k + 0.5) * width
            h = spring_z + _curve(half_span, rise, u)
            height = top_z - h
            if height < 0.02:
                continue
            spec = place(centre + u, -thick / 2.0, width * 1.04, thick,
                         height, (h + top_z) / 2.0)
            room.part(f"{name}_{k}", mat=mat, **spec)


def arch_ring(room, name, wall, centre, half_span, spring_z, *, rise=None,
              segments=13, band=0.2, proud=0.07, mat=None, plane=None,
              keystone=True):
    """A ring of voussoirs round an arch, standing proud of the wall face."""
    mat = mat or room.stone
    rise = half_span if rise is None else rise
    place = _frame(room, wall, plane)
    with room.piece(name):
        for k in range(segments):
            theta = math.pi * (k + 0.5) / segments
            # Point on the ellipse through the apex, band outside the curve.
            r_mid = half_span + band / 2.0
            u = r_mid * math.cos(theta)
            z = spring_z + (rise + band / 2.0) * math.sin(theta)
            arc = math.pi * (half_span + band / 2.0) / segments
            spec = place(centre + u, proud / 2.0 - 0.01, band, proud,
                         arc * 1.12, z, tilt=theta)
            room.part(f"{name}_voussoir_{k}", mat=mat, **spec)
        if keystone:
            spec = place(centre, proud / 2.0 + 0.015, band * 1.15, proud + 0.03,
                         band * 1.5, spring_z + rise + band / 2.0)
            room.part(f"{name}_keystone", mat=mat, **spec)
        # Jambs from the floor (or sill) up to the springing line.
        for k, side in enumerate((-1.0, 1.0)):
            u = side * (half_span + band / 2.0)
            spec = place(centre + u, proud / 2.0 - 0.01, band, proud,
                         spring_z, spring_z / 2.0)
            room.part(f"{name}_jamb_{k}", mat=mat, **spec)


def pilaster(room, name, y, top_z, *, width=0.5, proud=0.26, base=0.45):
    """A stone pilaster on the back wall: plinth, shaft, capital, abacus."""
    x = room.back_x
    with room.piece(name):
        room.part(f"{name}_plinth", (proud + 0.06, width + 0.1, base),
                  (x - (proud + 0.06) / 2.0, y, base / 2.0), room.stone)
        room.part(f"{name}_shaft", (proud, width, top_z - base - 0.45),
                  (x - proud / 2.0, y, base + (top_z - base - 0.45) / 2.0),
                  room.whitewash)
        room.part(f"{name}_flute_0", (proud + 0.015, 0.05, top_z - base - 0.5),
                  (x - proud / 2.0, y - width * 0.25,
                   base + (top_z - base - 0.5) / 2.0), room.plaster)
        room.part(f"{name}_flute_1", (proud + 0.015, 0.05, top_z - base - 0.5),
                  (x - proud / 2.0, y + width * 0.25,
                   base + (top_z - base - 0.5) / 2.0), room.plaster)
        room.part(f"{name}_capital", (proud + 0.1, width + 0.14, 0.3),
                  (x - (proud + 0.1) / 2.0, y, top_z - 0.3), room.stone)
        room.part(f"{name}_abacus", (proud + 0.16, width + 0.24, 0.1),
                  (x - (proud + 0.16) / 2.0, y, top_z - 0.05), room.stone)


def cornice(room, name, z, *, wall="back", y0=None, y1=None, proud=0.22):
    """A moulded stone band along a wall at height `z`."""
    place = _frame(room, wall)
    lo = -room.half_width if y0 is None else y0
    hi = room.half_width if y1 is None else y1
    if wall != "back":
        lo, hi = room.front_x, room.back_x
    mid = (lo + hi) / 2.0
    with room.piece(name):
        for index, (dz, out, h) in enumerate(((0.0, 0.1, 0.18),
                                              (0.14, 0.18, 0.1),
                                              (0.24, proud, 0.12))):
            spec = place(mid, out / 2.0, hi - lo, out, h, z + dz)
            room.part(f"{name}_{index}", mat=room.stone, **spec)


def window_tracery(room, name, y, z_spring, half_span, z_bottom, *, plane=None,
                   mat=None):
    """Iron glazing bars across a round-headed window: a mullion and a transom."""
    mat = mat or room.iron
    x = (room.back_x if plane is None else plane) - 0.05
    with room.piece(name):
        room.part(f"{name}_mullion", (0.04, 0.045, z_spring + half_span - z_bottom),
                  (x, y, (z_bottom + z_spring + half_span) / 2.0), mat)
        room.part(f"{name}_transom", (0.04, half_span * 2.0, 0.045),
                  (x, y, z_spring - 0.02), mat)
        room.part(f"{name}_transom_low", (0.04, half_span * 2.0, 0.045),
                  (x, y, z_bottom + (z_spring - z_bottom) * 0.45), mat)
        room.part(f"{name}_sill_bar", (0.04, half_span * 2.0, 0.045),
                  (x, y, z_bottom), mat)
        for k, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_jamb_bar_{k}", (0.04, 0.04, z_spring - z_bottom),
                      (x, y + side * (half_span - 0.02),
                       (z_spring + z_bottom) / 2.0), mat)
        # Heads of the two lights: short bars fanning up into the curve.
        for k, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_fan_{k}", (0.04, 0.04, half_span * 0.7),
                      (x, y + side * half_span * 0.5, z_spring + half_span * 0.4),
                      mat)


def tie_beams(room, name, ys, z, *, thick=0.26):
    """Beams across the nave at each truss, tying the roof across the hall."""
    span = room.back_x - room.front_x
    mid = (room.back_x + room.front_x) / 2.0
    with room.piece(name):
        for index, y in enumerate(ys):
            room.part(f"{name}_{index}", (span, thick, thick + 0.06),
                      (mid, y, z), room.wood)
            # Wall posts the beams land on, at the back wall.
            room.part(f"{name}_corbel_{index}", (0.3, thick + 0.1, 0.5),
                      (room.back_x - 0.15, y, z - 0.25), room.stone)


def hanging_lamp(room, name, at, z_top, z_lamp, *, lit=True, energy=55.0):
    """A *lampada*: a brass bowl on three chains from a tie beam."""
    x, y = at
    bowl_r = 0.2
    with room.piece(name):
        for k, (dx, dy) in enumerate(((0.12, 0.0), (-0.06, 0.1), (-0.06, -0.1))):
            room.part(f"{name}_chain_{k}", (0.02, 0.02, z_top - z_lamp),
                      (x + dx * 0.5, y + dy * 0.5, (z_top + z_lamp) / 2.0),
                      room.iron)
        room.part(f"{name}_ring", (0.3, 0.3, 0.03), (x, y, z_top - 0.02),
                  room.iron)
        with room.surface(z_lamp):
            furn._revolved(room, f"{name}_bowl", (x, y), (bowl_r, bowl_r),
                           ((0.35, 0.0), (0.8, 0.04), (1.0, 0.12), (1.05, 0.15)),
                           mat=room.bronze, sides=10)
        room.part(f"{name}_flame", (0.06, 0.06, 0.1),
                  (x, y, z_lamp + 0.19), room.lamplight if lit else room.wax)
    if lit:
        room.light(f"light_{name}", "POINT", (x, y, z_lamp + 0.3),
                   (0.0, 0.0, -1.0), energy, (1.0, 0.74, 0.44), radius=0.12)


def pulpit(room, name, y, *, floor_z=1.55, drum=0.55):
    """A pulpit (*pulpito*) bracketed from a pier: a drum, a rail, a canopy."""
    x = room.back_x - 0.55
    height = 0.95
    with room.piece(name):
        room.part(f"{name}_stem", (0.3, 0.3, floor_z), (x, y, floor_z / 2.0),
                  room.stone)
        furn._revolved(room, f"{name}_basin", (x, y), (drum, drum),
                       ((0.55, floor_z), (0.8, floor_z + 0.1),
                        (1.0, floor_z + 0.28), (1.04, floor_z + height)),
                       mat=room.wood, sides=8)
        # A gilt rail ring and a dark inset panel on the face that meets the nave.
        furn._revolved(room, f"{name}_rail", (x, y), (drum + 0.03, drum + 0.03),
                       ((1.0, floor_z + height - 0.06),
                        (1.0, floor_z + height + 0.02)),
                       mat=room.gilt, sides=8)
        room.part(f"{name}_panel", (0.04, drum * 0.9, height * 0.5),
                  (x - drum - 0.0, y, floor_z + height * 0.55), room.charcoal)
        # The sounding board over the pulpit, hung from the wall.
        room.part(f"{name}_canopy", (drum * 1.9, drum * 2.1, 0.08),
                  (x - 0.1, y, floor_z + height + 0.95), room.wood)
        room.part(f"{name}_canopy_gilt", (drum * 1.9 + 0.04, drum * 2.1 + 0.04, 0.03),
                  (x - 0.1, y, floor_z + height + 1.01), room.gilt)
        room.part(f"{name}_backboard", (0.06, drum * 1.5, height + 0.95),
                  (room.back_x - 0.06, y, floor_z + (height + 0.95) / 2.0),
                  room.wood)


def side_altar(room, name, y, depth, *, retable_height=3.4):
    """A gilt retable altar in a transept chapel, FACING the camera.

    `y` is the chapel's centre; `depth` is how far the chapel steps back. The
    altar is the same masonry block under a gilt-framed retable as
    `furnishings.altar`, here against the chapel's back wall instead of an end
    wall, so the whole face reads front-on.
    """
    plane = room.back_x + depth
    # altar() puts the retable 0.56 m behind the block's centre.
    furn.altar(room, name, (plane - 0.62 - 0.4, y), length=2.0, depth=0.8,
               height=1.05, retable_height=retable_height)


def chancel_candlestand(room, name, at, *, height=1.5):
    """A tall iron candlestand: a stem, a tray of tapers, two lit."""
    x, y = at
    with room.piece(name):
        room.part(f"{name}_foot", (0.28, 0.28, 0.05), (x, y, 0.025), room.iron)
        room.part(f"{name}_stem", (0.045, 0.045, height), (x, y, height / 2.0),
                  room.iron)
        room.part(f"{name}_tray", (0.34, 0.34, 0.03), (x, y, height), room.iron)
        for k, (dx, dy) in enumerate(((0.0, 0.0), (0.1, 0.1), (-0.1, -0.1),
                                      (0.1, -0.1), (-0.1, 0.1))):
            tall = 0.34 if k == 0 else 0.22
            room.part(f"{name}_candle_{k}", (0.06, 0.06, tall),
                      (x + dx, y + dy, height + 0.015 + tall / 2.0), room.wax)
            if k < 3:
                room.part(f"{name}_flame_{k}", (0.045, 0.045, 0.07),
                          (x + dx, y + dy, height + 0.015 + tall + 0.035),
                          room.lamplight)


def curtain(room, name, y, z0, z1, *, width=0.5, folds=4, mat=None, x=None):
    """A hung cloth drape on the back wall, gathered into vertical folds."""
    mat = mat or kit_material("red_wool")
    x = room.back_x - 0.05 if x is None else x
    step = width / folds
    with room.piece(name):
        room.part(f"{name}_rod", (0.06, width + 0.12, 0.05), (x - 0.02, y, z1 + 0.04),
                  room.bronze)
        for k in range(folds):
            dy = -width / 2.0 + (k + 0.5) * step
            out = 0.05 if k % 2 else 0.0
            room.part(f"{name}_fold_{k}", (0.05 + out, step * 1.05, z1 - z0),
                      (x - 0.025 - out / 2.0, y + dy, (z0 + z1) / 2.0), mat)


def kit_material(semantic_id):
    import interior as kit
    return kit.material(semantic_id)


def communion_rail(room, name, y, x0, x1, *, height=0.92, post_gap=0.22):
    """A turned-baluster rail (*grade*) across the chancel step, standing on
    `y`, running along X from `x0` to `x1`. Open between balusters."""
    length = x1 - x0
    mid = (x0 + x1) / 2.0
    count = max(2, int(length / post_gap))
    with room.piece(name):
        room.part(f"{name}_rail", (length, 0.14, 0.08), (mid, y, height), room.wood)
        room.part(f"{name}_rail_gilt", (length, 0.05, 0.02), (mid, y - 0.04, height + 0.05),
                  room.gilt)
        room.part(f"{name}_plinth", (length, 0.16, 0.1), (mid, y, 0.05), room.wood)
        for k in range(count + 1):
            x = x0 + length * k / count
            room.part(f"{name}_baluster_{k}", (0.07, 0.07, height - 0.1),
                      (x, y, (height + 0.1) / 2.0), room.wood)
        for k, x in enumerate((x0, x1)):
            room.part(f"{name}_newel_{k}", (0.16, 0.16, height + 0.18),
                      (x, y, (height + 0.18) / 2.0), room.wood)


def confessional(room, name, y, *, width=1.35, depth=0.95, height=2.55):
    """A confessional (*confessionario*): a dark timber booth against the far
    wall, a priest's cell between two penitents' doors with curtained fronts."""
    x = room.back_x - 0.4 - depth / 2.0
    cell = width * 0.4
    with room.piece(name):
        room.part(f"{name}_body", (depth, width, height), (x, y, height / 2.0), room.wood)
        room.part(f"{name}_cornice", (depth + 0.12, width + 0.12, 0.1),
                  (x - 0.02, y, height + 0.05), room.wood)
        room.part(f"{name}_gable", (depth * 0.7, width * 0.7, 0.28),
                  (x, y, height + 0.24), room.wood)
        for k, side in enumerate((-1.0, 1.0)):
            room.part(f"{name}_door_{k}", (0.05, cell * 0.78, height * 0.72),
                      (x - depth / 2.0 - 0.025, y + side * (width / 2.0 - cell / 2.0 - 0.04),
                       height * 0.4), room.charcoal)
            room.part(f"{name}_curtain_{k}", (0.04, cell * 0.7, height * 0.6),
                      (x - depth / 2.0 - 0.06, y + side * (width / 2.0 - cell / 2.0 - 0.04),
                       height * 0.42), kit_material("red_wool"))
        room.part(f"{name}_grille", (0.04, cell * 0.8, 0.5),
                  (x - depth / 2.0 - 0.03, y, height * 0.66), room.iron)
        room.part(f"{name}_priest_door", (0.05, cell, height * 0.85),
                  (x - depth / 2.0 - 0.025, y, height * 0.43), room.stone)
