"""The body builder: wings and courses resolved into one welded solid.

The whole module rests on one decision.  A wall is **not** a stack of boxes that
happen to touch; it is a rectilinear cell complex whose rails are the numbers
the recipe actually declares.  Every wing edge, every setback, every course
boundary and every aperture edge is promoted to a grid plane, the grid is
marked solid or void, and only the faces that separate solid from void are
emitted.  Three properties fall out of that which no amount of careful box
stacking gives you:

* Overlapping wings fuse.  Two wings sharing cells share no boundary between
  them, so an L-plan is one perimeter loop rather than two boxes intersecting.
* Nothing internal survives.  An interior face is by construction never emitted,
  so the "internal face survived the fuse" clause of :func:`records.validate`
  cannot fire, and we are not leaning on face cancellation to clean up after a
  guess about what is buried.
* Rails are real.  A cornice's projection splits the wall face along the course
  boundary because that boundary is a grid plane, which is exactly the edge loop
  a material change needs to land on.

Gable caps are the one thing outside the grid: a triangle is not a cell.  They
are emitted as a prism extruded ALONG THE RIDGE -- which is why
``extrude_axis == ridge_axis`` below is not a coincidence -- and the cells they
sit on are told not to emit their top face, so the cap needs no bottom.
"""

from __future__ import annotations

from .records import GrammarError, MeshBuilder, ModifierSpec, quantise

# Rails that land within this of each other are the same rail.  It is the
# records weld grid scaled up once: two rails computed by different routes
# (a setback plus a depth, versus a lane offset plus a half width) must not
# leave a sliver cell between them, and a sliver cell emits a face that
# validate() would then reject as degenerate.
RAIL_EPS = 1e-5


def _dedupe(values):
    ordered = sorted(quantise(value) for value in values)
    rails = []
    for value in ordered:
        if not rails or value - rails[-1] > RAIL_EPS:
            rails.append(value)
    return rails


class _Slab:
    """One course of one wing as an axis-aligned solid, already clipped."""

    __slots__ = ("wing", "course", "order", "x0", "x1", "y0", "y1", "z0", "z1")

    def __init__(self, wing, course, order, x0, x1, y0, y1, z0, z1):
        self.wing = wing
        self.course = course
        self.order = order
        self.x0, self.x1 = x0, x1
        self.y0, self.y1 = y0, y1
        self.z0, self.z1 = z0, z1

    def holds(self, x, y, z):
        return (self.x0 < x < self.x1 and self.y0 < y < self.y1
                and self.z0 < z < self.z1)


class _Void:
    """An aperture carved clean through the wall it sits on."""

    __slots__ = ("opening", "x0", "x1", "y0", "y1", "z0", "z1")

    def __init__(self, opening, x0, x1, y0, y1, z0, z1):
        self.opening = opening
        self.x0, self.x1 = x0, x1
        self.y0, self.y1 = y0, y1
        self.z0, self.z1 = z0, z1

    def holds(self, x, y, z):
        return (self.x0 < x < self.x1 and self.y0 < y < self.y1
                and self.z0 < z < self.z1)


def _wing_slabs(wing, mirrored):
    """Course rails for one wing, bottom up, with the mirror domain applied."""
    y0, y1 = wing.y_span()
    if mirrored:
        y0 = max(y0, 0.0)
    if y1 - y0 <= RAIL_EPS:
        return []
    back = quantise(wing.setback + wing.depth)
    slabs = []
    z = 0.0
    for order, course in enumerate(wing.courses):
        if course.kind == "gable_cap":
            # The cap is not a slab; it is handled against the roof section and
            # deliberately does not advance the eave.
            continue
        front = quantise(wing.setback + course.inset)
        if back - front <= RAIL_EPS:
            raise GrammarError(
                f"wing {wing.id}: course {course.kind} insets {course.inset} past "
                f"the wing's own depth {wing.depth}")
        top = quantise(z + course.height)
        slabs.append(_Slab(wing, course, order, front, back, y0, y1,
                           quantise(z), top))
        z = top
    return slabs


def _opening_void(recipe, opening, slabs_by_wing, mirrored):
    """Validate one aperture against its wing and turn it into a void.

    An opening is a hole in a WALL PLANE, so the run of courses it crosses has
    to present one plane: crossing a course whose inset differs would put the
    aperture half in a recess, and the reveals the assembly supplies would not
    meet the wall.  That -- not the course count -- is the boundary an opening
    "cannot fit inside".
    """
    wing = recipe.wing(opening.wing)
    slabs = slabs_by_wing.get(wing.id)
    if not slabs:
        return None
    oy0, oy1 = opening.y_span()
    wy0, wy1 = wing.y_span()
    # The jamb needs wall beside it; an aperture flush with the wing's return
    # is a corner with no masonry left to carry the lintel.
    if oy0 - opening.reveal < wy0 - RAIL_EPS or oy1 + opening.reveal > wy1 + RAIL_EPS:
        raise GrammarError(
            f"opening {opening.id}: spans {oy0}..{oy1} with a {opening.reveal} "
            f"reveal, which crosses the edge of wing {wing.id} ({wy0}..{wy1})")
    z0 = quantise(opening.sill_z)
    z1 = quantise(opening.sill_z + opening.height)
    if z0 < -RAIL_EPS:
        raise GrammarError(f"opening {opening.id}: sill {z0} is below ground")
    crossed = [slab for slab in slabs
               if slab.z1 - z0 > RAIL_EPS and z1 - slab.z0 > RAIL_EPS]
    if not crossed:
        raise GrammarError(
            f"opening {opening.id}: {z0}..{z1} sits outside every course of "
            f"wing {wing.id}")
    if z1 > max(slab.z1 for slab in crossed) + RAIL_EPS:
        raise GrammarError(
            f"opening {opening.id}: head at {z1} rises above the walls of wing "
            f"{wing.id}")
    # A step in the wall plane across the aperture is only survivable if the
    # assembly's own reveal is deep enough to bridge it: a door crossing a 60 mm
    # plinth projection still reads, the same door crossing a 220 mm cornice
    # leaves its head hanging in front of the wall.
    front = min(slab.course.inset for slab in crossed)
    step = max(slab.course.inset for slab in crossed) - front
    if step > opening.reveal + RAIL_EPS:
        raise GrammarError(
            f"opening {opening.id}: crosses a course boundary it cannot fit "
            f"inside -- courses "
            f"{sorted(slab.course.kind for slab in crossed)} of wing {wing.id} "
            f"step {step} in depth, more than its {opening.reveal} reveal")
    if mirrored:
        oy0 = max(oy0, 0.0)
        if oy1 - oy0 <= RAIL_EPS:
            return None
    # Pierce from the wing's most forward face to its back, so the aperture is a
    # hole rather than a niche with a face across the back of it.
    x0 = min(slab.x0 for slab in slabs)
    x1 = max(slab.x1 for slab in slabs)
    return _Void(opening, quantise(x0 - 1.0), quantise(x1 + 1.0),
                 oy0, oy1, z0, z1)


def _signed_area(section):
    total = 0.0
    for index in range(len(section)):
        a0, z0 = section[index]
        a1, z1 = section[(index + 1) % len(section)]
        total += a0 * z1 - a1 * z0
    return 0.5 * total


def _clip_positive(section):
    """Sutherland-Hodgman against ``a >= 0`` -- the mirror plane."""
    clipped = []
    count = len(section)
    for index in range(count):
        current = section[index]
        following = section[(index + 1) % count]
        inside_current = current[0] >= -RAIL_EPS
        inside_following = following[0] >= -RAIL_EPS
        if inside_current:
            clipped.append(current)
        if inside_current != inside_following:
            span = following[0] - current[0]
            if abs(span) > RAIL_EPS:
                t = -current[0] / span
                clipped.append((0.0, current[1] + t * (following[1] - current[1])))
    return clipped


def _add_prism(builder, section, extrude_axis, low, high, cap_semantic,
               side_semantic, *, skip_z, skip_cap_low, skip_side_at_zero):
    """A constant cross-section solid, wound outward.

    The section is CCW in its own (a, z) plane; the winding rules below are the
    right-hand rule read out once for each extrusion axis, and getting them
    wrong is invisible until Blender shades the roof from inside.
    """
    if _signed_area(section) < 0.0:
        section = list(reversed(section))
    count = len(section)
    if count < 3:
        return

    def point(a, z, other):
        if extrude_axis == "Y":
            return (a, other, z)
        return (other, a, z)

    ccw_at, reversed_at = (low, high) if extrude_axis == "Y" else (high, low)
    if not (skip_cap_low and ccw_at == low):
        builder.add_face([point(a, z, ccw_at) for a, z in section], cap_semantic)
    if not (skip_cap_low and reversed_at == low):
        builder.add_face([point(a, z, reversed_at) for a, z in reversed(section)],
                         cap_semantic)
    for index in range(count):
        a0, z0 = section[index]
        a1, z1 = section[(index + 1) % count]
        if abs(z0 - skip_z) <= RAIL_EPS and abs(z1 - skip_z) <= RAIL_EPS:
            continue  # the base edge: the cap sits on the wall, not on a floor
        if skip_side_at_zero and abs(a0) <= RAIL_EPS and abs(a1) <= RAIL_EPS:
            continue  # the cut through the mirror plane
        if extrude_axis == "Y":
            quad = [point(a0, z0, low), point(a0, z0, high),
                    point(a1, z1, high), point(a1, z1, low)]
        else:
            quad = [point(a0, z0, high), point(a0, z0, low),
                    point(a1, z1, low), point(a1, z1, high)]
        builder.add_face(quad, side_semantic)


def _gable_caps(recipe, wing, mirrored):
    """The triangular wall above the eave, shaped by the roof over this wing."""
    caps = []
    for course in wing.courses:
        if course.kind != "gable_cap":
            continue
        section = recipe.roof_section(wing.id)
        if section is None:
            raise GrammarError(
                f"wing {wing.id}: a gable_cap course has no roof section to take "
                "its shape from -- the cap is the wall UNDER a roof, so the roof "
                "is what decides its rise and ridge")
        eave = wing.eave_z
        x0 = quantise(wing.setback + course.inset)
        x1 = quantise(wing.setback + wing.depth)
        y0, y1 = wing.y_span()
        apex = quantise(eave + section.rise)
        if section.ridge_axis == "Y":
            # Ridge along the street: the triangle faces the returns and the
            # slopes present to the street, so the street semantic rides the
            # sloping sides.
            ridge_a = quantise((x0 + x1) / 2.0 + section.ridge_offset)
            profile = [(x0, eave), (x1, eave), (ridge_a, apex)]
            low, high = y0, y1
            if mirrored:
                low = max(low, 0.0)
                if high - low <= RAIL_EPS:
                    continue
            caps.append((profile, "Y", low, high,
                         course.return_semantic or course.semantic,
                         course.semantic, eave, mirrored and low == 0.0, False,
                         (x0, x1, y0 if not mirrored else low, y1)))
        else:
            ridge_a = quantise(wing.lane_offset + section.ridge_offset)
            profile = [(y0, eave), (y1, eave), (ridge_a, apex)]
            if mirrored:
                profile = _clip_positive(profile)
                if len(profile) < 3:
                    continue
            caps.append((profile, "X", x0, x1,
                         course.semantic,
                         course.return_semantic or course.semantic, eave,
                         False, mirrored,
                         (x0, x1, max(y0, 0.0) if mirrored else y0, y1)))
    return caps


def build_body(recipe):
    """Resolve a recipe's wings and courses into the single ``body`` record."""
    mirrored = "Y" in recipe.mirror_axes
    if mirrored and "Y" in recipe.baked_axes:  # recipe already refuses this
        raise GrammarError(f"recipe {recipe.id}: Y is both mirrored and baked")

    slabs = []
    slabs_by_wing = {}
    for wing in recipe.wings:
        own = _wing_slabs(wing, mirrored)
        slabs_by_wing[wing.id] = own
        slabs.extend(own)
    if not slabs:
        raise GrammarError(f"recipe {recipe.id}: no wing survives the build")

    caps = []
    for wing in recipe.wings:
        caps.extend(_gable_caps(recipe, wing, mirrored))

    voids = []
    cut = []
    for opening in recipe.openings:
        void = _opening_void(recipe, opening, slabs_by_wing, mirrored)
        if void is not None:
            voids.append(void)
            cut.append(opening.role)

    xs = _dedupe([value for slab in slabs for value in (slab.x0, slab.x1)]
                 + [value for cap in caps for value in cap[9][:2]])
    ys = _dedupe([value for slab in slabs for value in (slab.y0, slab.y1)]
                 + [value for void in voids for value in (void.y0, void.y1)]
                 + [value for cap in caps for value in cap[9][2:]])
    zs = _dedupe([value for slab in slabs for value in (slab.z0, slab.z1)]
                 + [value for void in voids for value in (void.z0, void.z1)])

    # Mark the grid.  A cell is identified by its index triple so neighbour
    # lookup is exact rather than a coordinate comparison.
    solid = {}
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2.0
        for j in range(len(ys) - 1):
            cy = (ys[j] + ys[j + 1]) / 2.0
            for k in range(len(zs) - 1):
                cz = (zs[k] + zs[k + 1]) / 2.0
                if any(void.holds(cx, cy, cz) for void in voids):
                    continue
                owner = None
                for slab in slabs:
                    if not slab.holds(cx, cy, cz):
                        continue
                    # The most forward course owns the face: a projecting
                    # cornice's own material is what the street sees.
                    if owner is None or (slab.x0, slab.order) < (owner.x0, owner.order):
                        owner = slab
                if owner is not None:
                    solid[(i, j, k)] = owner
    if not solid:
        raise GrammarError(f"recipe {recipe.id}: the body encloses no volume")

    builder = MeshBuilder(f"{recipe.id}_body")
    for (i, j, k), owner in sorted(solid.items()):
        low = (xs[i], ys[j], zs[k])
        high = (xs[i + 1], ys[j + 1], zs[k + 1])
        course = owner.course
        street = course.semantic
        ret = course.return_semantic or course.semantic
        semantics = {}
        if (i - 1, j, k) not in solid:
            semantics["-x"] = street
        if (i + 1, j, k) not in solid:
            semantics["+x"] = street
        if (i, j - 1, k) not in solid and not (mirrored and ys[j] <= RAIL_EPS):
            semantics["-y"] = ret
        if (i, j + 1, k) not in solid:
            semantics["+y"] = ret
        if (i, j, k - 1) not in solid:
            semantics["-z"] = street
        if (i, j, k + 1) not in solid and not _under_cap(caps, low, high):
            semantics["+z"] = street
        if semantics:
            builder.add_box_sided(low, high, semantics)

    for (profile, axis, low, high, cap_semantic, side_semantic, eave,
         skip_cap_low, skip_side_at_zero, _extent) in caps:
        _add_prism(builder, profile, axis, low, high, cap_semantic,
                   side_semantic, skip_z=eave, skip_cap_low=skip_cap_low,
                   skip_side_at_zero=skip_side_at_zero)

    origin = (min(wing.setback for wing in recipe.wings), 0.0, 0.0)
    modifiers = (ModifierSpec("MIRROR", axes=("Y",)),) if mirrored else ()
    metadata = {
        "wings": [wing.id for wing in recipe.wings],
        "eaveZ": {wing.id: wing.eave_z for wing in recipe.wings},
        "openings": cut,
    }
    return builder.record("body", origin=origin, parent_role=None,
                          modifiers=modifiers, metadata=metadata)


def _under_cap(caps, low, high):
    """Is this cell's top face the floor of a gable cap rather than a roofline?

    Suppressing it here is what lets the cap be emitted without a bottom face:
    the cap footprint spans many cells, so the two faces would never have been
    coincident enough to cancel.
    """
    cx = (low[0] + high[0]) / 2.0
    cy = (low[1] + high[1]) / 2.0
    for cap in caps:
        x0, x1, y0, y1 = cap[9]
        if abs(high[2] - cap[6]) > RAIL_EPS:
            continue
        if x0 - RAIL_EPS < cx < x1 + RAIL_EPS and y0 - RAIL_EPS < cy < y1 + RAIL_EPS:
            return True
    return False
