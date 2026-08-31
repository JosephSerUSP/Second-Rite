"""Doors and windows: one record per opening assembly.

The member vocabulary and every constant below come from ``exterior.doorway``
and ``exterior.window``, which are the owner-approved openings.  Two decisions
carried over from there are the whole reason this builder is shaped the way it
is:

* the surround is **layered members**, never a slab.  A solid rectangle behind
  the leaf reads as a pasted-on rectangle at native resolution; a threshold, a
  pair of jambs, a lintel and a recessed leaf read as depth.
* a window pane gets a small wood frame and a mullion, because an unbroken
  dark quad reads as a black void rather than as glass.

All of it lands in ONE record.  The members are disconnected islands inside
that record, which the contract allows on purpose: an opening is one thing to
select, hand-edit and rotate, not eleven sparse boxes.

**Frame.**  The building frame of :mod:`records`: +X into the building away
from the street, +Y along the street, +Z up.  So the street face of the host
wing is the X origin of the assembly and everything that projects toward the
viewer projects along -X.  The record's own origin is the opening's centre at
ground level -- the wing's street face, the opening's absolute ``lane_offset``,
Z=0 -- so a hand-edited door swings about its own doorway rather than about the
building's lane centre.

**Openings are never mirrored.**  Even under ``mirror_axes=("Y",)`` every
opening is emitted explicitly at its own lane offset with no modifier attached:
a mirror would move a door that the runtime anchors by lane position, and an
off-centre door under a symmetric façade is the ordinary case, not the
exception.
"""

from __future__ import annotations

from .records import GrammarError, MeshBuilder

# Semantics.  Named once so the authored language -- leaf and frame dark wood,
# surround limestone, drip terracotta -- is stated rather than repeated.
WOOD = "dark_wood"
STONE = "rough_limestone"
TERRACOTTA = "terracotta"
IRON = "wrought_iron"
GLASS = "smoked_glass"

# Measured members, all read off exterior.doorway/exterior.window.
LEAF_THICKNESS = 0.12
PANE_THICKNESS = 0.06
JAMB_PROJECTION = 0.16
LINTEL_HEIGHT = 0.24
LINTEL_MARGIN = 0.25          # the lintel oversails the jambs; that is the look
DRIP_HEIGHT = 0.10
DRIP_MARGIN = 0.34
DRIP_PROJECTION = 0.34
THRESHOLD_DEPTH = 0.52        # a door threshold reaches into the street...
SILL_DEPTH = 0.38             # ...further than a window sill does
THRESHOLD_HEIGHT = 0.16
SILL_HEIGHT = 0.14
THRESHOLD_MARGIN = 0.21
SILL_MARGIN = 0.23
FRAME_MEMBER = 0.08
MULLION_WIDTH = 0.07
FRAME_THICKNESS = 0.08
SHUTTER_THICKNESS = 0.08
SHUTTER_FRACTION = 0.52       # folded back, a shutter covers half its opening
SHUTTER_STANDOFF = 0.76       # ...and sits this many widths off centre
GRILLE_THICKNESS = 0.06
GRILLE_BAR = 0.03
GRILLE_SPACING = 0.16         # bars this far apart still read as bars at 256x240
PEDIMENT_RISE = 0.40
PANEL_RELIEF = 0.02
PANEL_MARGIN = 0.10           # the stile left around a raised panel
STALL_DEPTH = 0.44
STALL_HEIGHT = 0.09

# The lining of the reveal.  Thin enough that it reads as a returned wall face
# rather than as a second frame inside the first.
REVEAL_LINING = 0.05


class _Placed:
    """A builder that accepts opening-local coordinates.

    Members are far easier to read authored about the opening's own centre,
    but :meth:`MeshBuilder.record` subtracts the origin from what it was given,
    so the builder has to be fed building-frame coordinates.  This translates
    once, here, instead of every member carrying the wing's street face and the
    lane offset through its arithmetic.
    """

    def __init__(self, name, origin):
        self._builder = MeshBuilder(name)
        self._origin = origin

    def _shift(self, point):
        return tuple(value + offset for value, offset in zip(point, self._origin))

    def add_box(self, low, high, semantic):
        return self._builder.add_box(self._shift(low), self._shift(high), semantic)

    def add_face(self, points, semantic):
        return self._builder.add_face([self._shift(point) for point in points],
                                      semantic)

    def record(self, *args, **kwargs):
        return self._builder.record(*args, **kwargs)


class _Profile:
    """One register of the opening language.

    A profile is not a different builder; it is a handful of scalars plus which
    optional members it forces on.  Keeping it that way is what stops "civic"
    from quietly becoming a second, divergent door.
    """

    def __init__(self, reveal_scale=1.0, pediment=False, stall=False):
        self.reveal_scale = reveal_scale
        self.pediment = pediment
        self.stall = stall


PROFILES = {
    "plain": _Profile(),
    # A shopfront sits shallow in the wall and puts a board out over the
    # street: the goods are the display, so the opening must not swallow them.
    "shop": _Profile(reveal_scale=0.65, stall=True),
    # The civic register buys its authority with depth and a head.
    "civic": _Profile(reveal_scale=1.6, pediment=True),
}


def build_openings(recipe):
    """Every opening of ``recipe``, in recipe order, one record each."""
    return [_build_opening(recipe, opening) for opening in recipe.openings]


# -- one assembly ---------------------------------------------------------
def _build_opening(recipe, opening):
    profile = PROFILES.get(opening.profile)
    if profile is None:
        raise GrammarError(
            f"opening {opening.id}: unknown profile {opening.profile!r} "
            f"(known: {', '.join(sorted(PROFILES))})")

    wing = recipe.wing(opening.wing)
    _check_span(opening, wing)

    face_x = wing.x_span()[0]
    origin = (face_x, opening.lane_offset, 0.0)

    # Everything below is authored relative to that origin, so the arithmetic
    # is about the opening and never about where the building stands.
    reveal = opening.reveal * profile.reveal_scale
    half = opening.width / 2.0
    y0, y1 = -half, half
    z0 = opening.sill_z
    z1 = opening.sill_z + opening.height

    builder = _Placed(f"{opening.kind}_{opening.id}", origin)

    _add_reveal(builder, reveal, y0, y1, z0, z1)
    _add_jambs(builder, opening, reveal, half, z0, z1)
    head_top = _add_head(builder, opening, profile, half, z1)
    _add_base(builder, opening, profile, half, z0)

    if opening.kind == "door":
        _add_leaf(builder, opening, reveal, y0, y1, z0, z1)
    else:
        _add_glazing(builder, reveal, y0, y1, z0, z1)

    if opening.grille:
        _add_grille(builder, reveal, y0, y1, z0, z1)
    if opening.shutters:
        _add_shutters(builder, opening, half, z0, z1)

    record = builder.record(
        opening.role, origin=origin, parent_role="body",
        # No modifier, ever: see the module docstring.
        modifiers=(),
        metadata={"kind": opening.kind, "profile": opening.profile,
                  "lit": bool(opening.lit)},
    )
    _check_bounds(record, opening, wing, head_top)
    return record


# -- members --------------------------------------------------------------
def _add_reveal(builder, reveal, y0, y1, z0, z1):
    """The four surfaces lining the hole the body builder cut.

    A ring, not a panel: the middle of the opening belongs to the leaf or the
    pane, and filling it here is exactly the pasted-rectangle failure.
    """
    lining = min(REVEAL_LINING, (y1 - y0) / 4.0, (z1 - z0) / 4.0)
    builder.add_box((0.0, y0, z0), (reveal, y1, z0 + lining), STONE)
    builder.add_box((0.0, y0, z1 - lining), (reveal, y1, z1), STONE)
    builder.add_box((0.0, y0, z0 + lining), (reveal, y0 + lining, z1 - lining), STONE)
    builder.add_box((0.0, y1 - lining, z0 + lining), (reveal, y1, z1 - lining), STONE)


def _add_jambs(builder, opening, reveal, half, z0, z1):
    """The pair of stone members flanking the opening, ``jamb`` wide.

    They project toward the street rather than sitting flush, which is what
    gives the leaf a shadow to sit in at this pixel scale.
    """
    projection = -JAMB_PROJECTION
    top = z1 + 0.09
    for side in (-1.0, 1.0):
        inner = side * half
        outer = side * (half + opening.jamb)
        builder.add_box((projection, min(inner, outer), z0),
                        (reveal, max(inner, outer), top), STONE)


def _add_head(builder, opening, profile, half, z1):
    """Lintel, drip and pediment.  Returns the top Z the assembly reaches."""
    top = z1
    if opening.lintel:
        top = z1 + LINTEL_HEIGHT
        builder.add_box((-JAMB_PROJECTION - 0.1, -(half + LINTEL_MARGIN), z1),
                        (0.0, half + LINTEL_MARGIN, top), STONE)
    if opening.drip:
        # The drip oversails the lintel in both depth and width; that overhang
        # is the whole point of it, so it is not parameterised away.
        builder.add_box((-DRIP_PROJECTION, -(half + DRIP_MARGIN), top),
                        (0.0, half + DRIP_MARGIN, top + DRIP_HEIGHT),
                        TERRACOTTA)
        top += DRIP_HEIGHT
    if opening.pediment or profile.pediment:
        _add_pediment(builder, half, top)
        top += PEDIMENT_RISE
    return top


def _add_pediment(builder, half, base_z):
    """A triangular head, as a prism rather than a flat gable board.

    Built face by face because a triangle is not a box, and the civic register
    is the one place the grammar needs a non-rectangular member.
    """
    back = 0.0
    front = -(JAMB_PROJECTION + 0.12)
    y0 = -(half + LINTEL_MARGIN)
    y1 = half + LINTEL_MARGIN
    apex = base_z + PEDIMENT_RISE
    for x, order in ((front, (( y0, base_z), (y1, base_z), (0.0, apex))),
                     (back, ((y1, base_z), (y0, base_z), (0.0, apex)))):
        builder.add_face([(x, y, z) for y, z in order], STONE)
    builder.add_face([(front, y0, base_z), (back, y0, base_z),
                      (back, y1, base_z), (front, y1, base_z)], STONE)
    builder.add_face([(front, y0, base_z), (front, 0.0, apex),
                      (back, 0.0, apex), (back, y0, base_z)], STONE)
    builder.add_face([(front, y1, base_z), (back, y1, base_z),
                      (back, 0.0, apex), (front, 0.0, apex)], STONE)


def _add_base(builder, opening, profile, half, z0):
    """Sill for a window, threshold for a door, plus a shopfront stall board.

    A door's threshold reaches further into the street than a window's sill
    because a threshold is walked on and a sill is only leaned out of.
    """
    if opening.sill:
        door = opening.kind == "door"
        depth = THRESHOLD_DEPTH if door else SILL_DEPTH
        height = THRESHOLD_HEIGHT if door else SILL_HEIGHT
        margin = THRESHOLD_MARGIN if door else SILL_MARGIN
        low_z = z0 if door else z0 - height
        builder.add_box((-depth, -(half + margin), low_z),
                        (0.0, half + margin, low_z + height), STONE)
    if profile.stall:
        # The board a shop trades over: wood, out past the sill, at sill level.
        builder.add_box((-(SILL_DEPTH + STALL_DEPTH), -(half + SILL_MARGIN),
                         z0 - SILL_HEIGHT - STALL_HEIGHT),
                        (-SILL_DEPTH * 0.5, half + SILL_MARGIN,
                         z0 - SILL_HEIGHT), WOOD)


def _add_leaf(builder, opening, reveal, y0, y1, z0, z1):
    """A door leaf, recessed into the reveal, optionally with raised panels."""
    builder.add_box((reveal, y0, z0), (reveal + LEAF_THICKNESS, y1, z1), WOOD)
    if opening.panels <= 0:
        return
    # Panels are raised OUT of the leaf toward the street.  Sinking them
    # instead would need the leaf cut, and a cut leaf cannot be hand-edited as
    # one slab afterwards.
    count = opening.panels
    inner_y0 = y0 + PANEL_MARGIN
    inner_y1 = y1 - PANEL_MARGIN
    span = (z1 - z0) - PANEL_MARGIN * (count + 1)
    if inner_y1 - inner_y0 <= 0.0 or span <= 0.0:
        raise GrammarError(
            f"opening {opening.id}: {count} panels do not fit a "
            f"{opening.width} x {opening.height} leaf")
    each = span / count
    for index in range(count):
        low = z0 + PANEL_MARGIN * (index + 1) + each * index
        builder.add_box((reveal - PANEL_RELIEF, inner_y0, low),
                        (reveal, inner_y1, low + each), WOOD)


def _add_glazing(builder, reveal, y0, y1, z0, z1):
    """Pane, frame and mullion.

    The pane keeps ``smoked_glass`` even when the opening is lit: emissive
    materials are per-scene and the grammar is scene-free, so the record says
    ``lit`` in its metadata and the emitter does the swap.
    """
    builder.add_box((reveal, y0, z0), (reveal + PANE_THICKNESS, y1, z1), GLASS)
    front = reveal - 0.02
    back = reveal + FRAME_THICKNESS * 0.5
    builder.add_box((front, y0, z1 - FRAME_MEMBER), (back, y1, z1), WOOD)
    builder.add_box((front, y0, z0), (back, y1, z0 + FRAME_MEMBER), WOOD)
    builder.add_box((front, -MULLION_WIDTH / 2.0, z0),
                    (back, MULLION_WIDTH / 2.0, z1), WOOD)


def _add_grille(builder, reveal, y0, y1, z0, z1):
    """Wrought iron in front of the pane: vertical bars plus two rails."""
    front = reveal - GRILLE_THICKNESS - 0.02
    back = reveal - 0.02
    width = y1 - y0
    bars = max(2, int(round(width / GRILLE_SPACING)))
    for index in range(bars):
        centre = y0 + width * (index + 0.5) / bars
        builder.add_box((front, centre - GRILLE_BAR / 2.0, z0),
                        (back, centre + GRILLE_BAR / 2.0, z1), IRON)
    for level in (z0 + (z1 - z0) * 0.25, z0 + (z1 - z0) * 0.75):
        builder.add_box((front, y0, level - GRILLE_BAR / 2.0),
                        (back, y1, level + GRILLE_BAR / 2.0), IRON)


def _add_shutters(builder, opening, half, z0, z1):
    """A pair folded back flat against the wall, not swung into the street."""
    leaf = opening.width * SHUTTER_FRACTION
    for side in (-1.0, 1.0):
        centre = side * opening.width * SHUTTER_STANDOFF
        builder.add_box((-SHUTTER_THICKNESS, centre - leaf / 2.0, z0),
                        (0.0, centre + leaf / 2.0, z1), WOOD)


# -- validation -----------------------------------------------------------
def _check_span(opening, wing):
    """The cheap checks, run before any geometry exists.

    Reported against the opening rather than against whichever member happened
    to be degenerate first, because "door_main is wider than wing front" is a
    recipe bug the author can act on and "degenerate box" is not.
    """
    oy0, oy1 = opening.y_span()
    wy0, wy1 = wing.y_span()
    if oy0 < wy0 or oy1 > wy1:
        raise GrammarError(
            f"opening {opening.id}: spans Y {oy0}..{oy1}, past wing "
            f"{wing.id} span {wy0}..{wy1}")
    if opening.sill_z < 0.0:
        raise GrammarError(
            f"opening {opening.id}: sill_z {opening.sill_z} is below ground Z=0")
    if opening.sill_z + opening.height > wing.eave_z:
        raise GrammarError(
            f"opening {opening.id}: head reaches Z "
            f"{opening.sill_z + opening.height}, above wing {wing.id} eave_z "
            f"{wing.eave_z}")


def _check_bounds(record, opening, wing, head_top):
    """The same three constraints, now against every member that was built.

    A lintel oversails its jambs and a drip oversails the lintel, so an opening
    that fits can still put stone past the end of its own wing.
    """
    (_, min_y, min_z), (_, max_y, max_z) = record.bounds()
    lane = opening.lane_offset
    wy0, wy1 = wing.y_span()
    if lane + min_y < wy0 or lane + max_y > wy1:
        raise GrammarError(
            f"opening {opening.id}: members reach Y {lane + min_y}.."
            f"{lane + max_y}, past wing {wing.id} span {wy0}..{wy1}")
    if min_z < 0.0:
        raise GrammarError(
            f"opening {opening.id}: members reach Z {min_z}, below ground Z=0")
    if max(max_z, head_top) > wing.eave_z:
        raise GrammarError(
            f"opening {opening.id}: members reach Z {max(max_z, head_top)}, "
            f"above wing {wing.id} eave_z {wing.eave_z}")
