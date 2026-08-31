"""The body builder: a plan outline swept through a course stack.

The previous builder was a rectilinear cell complex, and it was wrong in a way
tuning does not reach.  A grid can only emit axis-aligned quads, and the
authored St. Maria houses carry nine slanted faces out of twenty-nine; the same
choice emitted one quad per cell face, so a plain townhouse came out at 466
faces against the authored 29.  Both complaints are one representation.

So the body is a **sweep**.  Two independent objects meet:

* a **plan outline** -- one CCW perimeter loop per island, taken from the union
  of the wing rectangles, with a pier substituted at each convex corner; and
* a **course stack** -- the z bands the courses resolve into.

Their product is the wall: one quad per (plan edge x band).  A wall is one edge
rather than a row of cells, so coplanar merging along it is free rather than a
post-pass, and a face that is not axis-aligned is no harder to emit than one
that is -- which is the whole point.

Three consequences worth spelling out, because each one was a decision:

* **A course transition is a splay, not a step.**  Where a course changes its
  inset by ``d``, the default is a 45 degree band of height ``|d|`` taken from
  the BOTTOM of the upper course, which is where the authored eave sits (main
  wall to 4.6, splay 4.6..4.7, cornice 4.7..5.0).  Taking it from the upper
  course rather than inserting it is what keeps ``Wing.eave_z`` -- which the
  roof builder reads -- equal to the sum of the declared heights.
  ``Course.transition="step"`` restores the square return for a building that
  wants one.
* **An inset offsets the whole outline, not just the street face.**  A cornice
  that projects on the front and stops at the corner is not a cornice.  The
  design doc records the authored cornice as "wall + 0.1, continuous", and the
  pier stopping at the eave while the cornice carries on around is only
  meaningful if the cornice is a continuous band.  This is a deliberate change
  from the cell complex, which moved the front plane only.
* **The pier is a property of a range of courses.**  ``PierSpec.through`` names
  the last course it runs through; above that the outline reverts to the plain
  loop and the difference is capped by one hexagon per corner.

Openings remain the one place a wall panel is subdivided, and they subdivide
only the panel they pierce: the sub-cells are merged greedily back into
rectangles, so two windows in one storey cost five faces rather than fifteen.

Gable caps stay outside the sweep, because a triangle is not a band.  They are
extruded ALONG THE RIDGE against the top band's footprint, and that band's top
cap is suppressed so the cap needs no bottom.
"""

from __future__ import annotations

import math

from .records import GrammarError, MeshBuilder, ModifierSpec, quantise

# Rails and outline points that land within this of each other are the same.
# It is the records weld grid scaled up once: two values computed by different
# routes (a setback plus a depth, versus a lane offset plus a half width) must
# not leave a sliver, and a sliver emits a face validate() calls degenerate.
RAIL_EPS = 1e-5


# --------------------------------------------------------------------------
# plan geometry
# --------------------------------------------------------------------------

def _dedupe(values):
    ordered = sorted(quantise(value) for value in values)
    rails = []
    for value in ordered:
        if not rails or value - rails[-1] > RAIL_EPS:
            rails.append(value)
    return rails


def _unit(vector):
    length = math.hypot(vector[0], vector[1])
    if length <= RAIL_EPS:
        return None
    return (vector[0] / length, vector[1] / length)


def _outward(direction):
    """Outward normal of a CCW-wound edge running in ``direction``."""
    return (direction[1], -direction[0])


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _wing_rect(wing, mirror_x, mirror_y):
    """One wing's footprint, clipped to the fundamental domain."""
    x0, x1 = wing.x_span()
    y0, y1 = wing.y_span()
    if mirror_x:
        x0 = max(x0, 0.0)
    if mirror_y:
        y0 = max(y0, 0.0)
    if x1 - x0 <= RAIL_EPS or y1 - y0 <= RAIL_EPS:
        return None
    return (x0, x1, y0, y1)


def _trace_loops(rects):
    """The perimeter loops of a union of axis-aligned rectangles, CCW.

    This is the one place the old cell complex was right and must not be
    regressed: an L-plan has to come out as ONE loop, not two rectangles
    intersecting.  So the union is marked on a rail grid and only the cell
    edges that separate solid from void are kept -- the same criterion as
    before, applied in 2D where it costs four edges rather than a whole
    building's worth of quads.
    """
    xs = _dedupe([value for rect in rects for value in rect[:2]])
    ys = _dedupe([value for rect in rects for value in rect[2:]])
    solid = set()
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2.0
        for j in range(len(ys) - 1):
            cy = (ys[j] + ys[j + 1]) / 2.0
            for x0, x1, y0, y1 in rects:
                if x0 < cx < x1 and y0 < cy < y1:
                    solid.add((i, j))
                    break
    if not solid:
        raise GrammarError("the plan outline encloses no area")

    edges = {}
    for i, j in solid:
        x0, x1 = xs[i], xs[i + 1]
        y0, y1 = ys[j], ys[j + 1]
        if (i, j - 1) not in solid:
            edges[(x0, y0)] = (x1, y0)
        if (i + 1, j) not in solid:
            edges[(x1, y0)] = (x1, y1)
        if (i, j + 1) not in solid:
            edges[(x1, y1)] = (x0, y1)
        if (i - 1, j) not in solid:
            edges[(x0, y1)] = (x0, y0)

    loops = []
    while edges:
        start = next(iter(edges))
        loop = [start]
        point = edges.pop(start)
        while point != start:
            loop.append(point)
            point = edges.pop(point)
        loops.append(_merge_collinear(loop))
    return loops


def _merge_collinear(loop):
    """Drop vertices that only sit in the middle of a straight run.

    A rail grid puts a vertex wherever any wing's edge crosses; leaving them in
    would reintroduce the per-cell face count through the back door.
    """
    merged = []
    count = len(loop)
    for index in range(count):
        previous = loop[(index - 1) % count]
        current = loop[index]
        following = loop[(index + 1) % count]
        incoming = _unit((current[0] - previous[0], current[1] - previous[1]))
        outgoing = _unit((following[0] - current[0], following[1] - current[1]))
        if incoming is None or outgoing is None:
            continue
        if abs(_cross(incoming, outgoing)) <= RAIL_EPS and \
                incoming[0] * outgoing[0] + incoming[1] * outgoing[1] > 0.0:
            continue
        merged.append(current)
    return merged


def _signed_area_2d(loop):
    total = 0.0
    for index in range(len(loop)):
        x0, y0 = loop[index]
        x1, y1 = loop[(index + 1) % len(loop)]
        total += x0 * y1 - x1 * y0
    return 0.5 * total


def _corner_frame(loop, index):
    """``(incoming, outgoing)`` unit directions at one outline vertex."""
    count = len(loop)
    current = loop[index]
    previous = loop[(index - 1) % count]
    following = loop[(index + 1) % count]
    return (_unit((current[0] - previous[0], current[1] - previous[1])),
            _unit((following[0] - current[0], following[1] - current[1])))


def _apply_pier(loop, pier):
    """Replace every convex corner of ``loop`` with the pier's six-point run.

    The five emitted points are the design doc's measured outline read back as
    a construction rather than as coordinates:

        a = C - u*(width/2 + splay)    leave the wall plane
        b = C - u*(width/2) + n_u*project    arrive at the pier face
        c = C + u*(width/2) + n_u*project    along the incoming wall
        d = C + v*(width/2) + n_v*project    along the outgoing wall
        e = C + v*(width/2 + splay)    return to the wall plane

    with ``u``/``v`` the incoming and outgoing directions and ``n`` their
    outward normals.  At the authored 90 degree corner ``c`` and the outgoing
    face's start coincide, which is why the measured run reads as five segments
    and not six.
    """
    count = len(loop)
    replaced = []
    for index in range(count):
        current = loop[index]
        incoming, outgoing = _corner_frame(loop, index)
        if incoming is None or outgoing is None or _cross(incoming, outgoing) <= RAIL_EPS:
            replaced.append(current)
            continue
        reach = pier.width / 2.0 + pier.splay
        previous = loop[(index - 1) % count]
        following = loop[(index + 1) % count]
        if math.dist(current, previous) < 2.0 * reach - RAIL_EPS or \
                math.dist(current, following) < 2.0 * reach - RAIL_EPS:
            raise GrammarError(
                f"pier at corner {current} needs {reach} of wall on each side, "
                "and the outline does not have it -- shorten width/splay or "
                "widen the wing")
        n_in = _outward(incoming)
        n_out = _outward(outgoing)
        half = pier.width / 2.0
        replaced.extend([
            (current[0] - incoming[0] * reach, current[1] - incoming[1] * reach),
            (current[0] - incoming[0] * half + n_in[0] * pier.project,
             current[1] - incoming[1] * half + n_in[1] * pier.project),
            (current[0] + incoming[0] * half + n_in[0] * pier.project,
             current[1] + incoming[1] * half + n_in[1] * pier.project),
            (current[0] + outgoing[0] * half + n_out[0] * pier.project,
             current[1] + outgoing[1] * half + n_out[1] * pier.project),
            (current[0] + outgoing[0] * reach, current[1] + outgoing[1] * reach),
        ])
    return _merge_collinear(replaced)


def _offset(loop, distance, mirror_axes=()):
    """Push every edge of a CCW loop ``distance`` outward, mitring the corners.

    The mitre is the standard bisector formula, and it is what makes two splays
    meeting at a corner join along one edge instead of leaving a notch -- the
    authored file's ``(-0.577, -0.577, 0.577)`` face is that join.
    """
    if abs(distance) <= RAIL_EPS:
        return list(loop)
    moved = []
    for index in range(len(loop)):
        current = loop[index]
        incoming, outgoing = _corner_frame(loop, index)
        n_in = _outward(incoming)
        n_out = _outward(outgoing)
        denominator = 1.0 + n_in[0] * n_out[0] + n_in[1] * n_out[1]
        if denominator <= RAIL_EPS:
            raise GrammarError(
                f"outline reverses on itself at {current}; an inset cannot be "
                "offset through a zero-width spur")
        scale = distance / denominator
        x = current[0] + (n_in[0] + n_out[0]) * scale
        y = current[1] + (n_in[1] + n_out[1]) * scale
        # An editable mirror owns the other half of the solid.  Its cut plane
        # must stay put while the authored perimeter expands around it, or a
        # projected course crosses the plane and overlaps its mirrored copy.
        if "X" in mirror_axes and abs(current[0]) <= RAIL_EPS:
            x = 0.0
        if "Y" in mirror_axes and abs(current[1]) <= RAIL_EPS:
            y = 0.0
        moved.append((x, y))
    return moved


# --------------------------------------------------------------------------
# the course stack
# --------------------------------------------------------------------------

class _Band:
    """One z band of the sweep: two outlines and the course that owns them.

    ``z0 == z1`` is legal and is exactly what ``transition="step"`` produces --
    a horizontal ring whose quads come out of the same winding rule as a wall's.
    """

    __slots__ = ("z0", "z1", "course", "inset_low", "inset_high", "kind")

    def __init__(self, z0, z1, course, inset_low, inset_high, kind):
        self.z0, self.z1 = z0, z1
        self.course = course
        self.inset_low, self.inset_high = inset_low, inset_high
        self.kind = kind  # "wall", "splay" or "step"


def _course_stack(wing):
    """Resolve one wing's courses into bands, bottom up.

    Gable caps are skipped here on purpose: a cap is not a band and it
    deliberately does not advance the eave, so the stack a roof reads against
    stays the sum of the non-cap heights.
    """
    bands = []
    z = 0.0
    previous = None
    for course in wing.courses:
        if course.kind == "gable_cap":
            continue
        if quantise(wing.depth - abs(course.inset)) <= RAIL_EPS and course.inset > 0.0:
            raise GrammarError(
                f"wing {wing.id}: course {course.kind} insets {course.inset} past "
                f"the wing's own depth {wing.depth}")
        height = course.height
        if previous is not None and abs(course.inset - previous) > RAIL_EPS:
            change = abs(course.inset - previous)
            if course.transition == "splay":
                if change >= height - RAIL_EPS:
                    raise GrammarError(
                        f"wing {wing.id}: course {course.kind} changes inset by "
                        f"{change} but is only {height} tall -- a splay is taken "
                        "from the bottom of the course it belongs to, so the "
                        "course must be taller than the change")
                bands.append(_Band(quantise(z), quantise(z + change), course,
                                   previous, course.inset, "splay"))
                z = quantise(z + change)
                height = quantise(height - change)
            else:
                bands.append(_Band(quantise(z), quantise(z), course,
                                   previous, course.inset, "step"))
        bands.append(_Band(quantise(z), quantise(z + height), course,
                           course.inset, course.inset, "wall"))
        z = quantise(z + height)
        previous = course.inset
    if not bands:
        raise GrammarError(f"wing {wing.id}: every course is a gable cap")
    return bands


def _shared_stack(recipe):
    """The one course stack the sweep applies to the whole outline.

    A sweep has a single course stack by construction.  Wings that disagree are
    refused rather than approximated, because the alternative -- sweeping each
    wing separately -- puts the shared wall back inside the solid, which is the
    exact defect the union outline exists to avoid.
    """
    stacks = {wing.id: _course_stack(wing) for wing in recipe.wings}
    reference = recipe.wings[0]
    for wing in recipe.wings[1:]:
        if tuple(wing.courses) != tuple(reference.courses):
            raise GrammarError(
                f"recipe {recipe.id}: wings {reference.id!r} and {wing.id!r} "
                "declare different course stacks, and a swept body has one "
                "stack -- give them the same courses, or model them as two "
                "buildings")
    return stacks[reference.id]


# --------------------------------------------------------------------------
# openings
# --------------------------------------------------------------------------

class _Hole:
    """An aperture reduced to a rectangle in (lane, height) on one wall."""

    __slots__ = ("opening", "a0", "a1", "z0", "z1")

    def __init__(self, opening, a0, a1, z0, z1):
        self.opening = opening
        self.a0, self.a1 = a0, a1
        self.z0, self.z1 = z0, z1


def _opening_hole(recipe, opening, bands, mirror_y):
    """Validate one aperture against its wing and turn it into a hole.

    Every check here is carried over from the cell complex unchanged, because
    each one encodes a real constraint rather than an artefact of the old
    representation.  An opening is a hole in a WALL PLANE, so the run of
    courses it crosses has to present one plane: crossing a course whose inset
    differs would put the aperture half in a recess, and the reveals the
    assembly supplies would not meet the wall.  That -- not the course count --
    is the boundary an opening "cannot fit inside".
    """
    wing = recipe.wing(opening.wing)
    oy0, oy1 = opening.y_span()
    wy0, wy1 = (wing.y_span() if opening.elevation in ("front", "back")
                else wing.x_span())
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
    crossed = [band for band in bands
               if band.z1 - z0 > RAIL_EPS and z1 - band.z0 > RAIL_EPS]
    if not crossed:
        raise GrammarError(
            f"opening {opening.id}: {z0}..{z1} sits outside every course of "
            f"wing {wing.id}")
    if z1 > max(band.z1 for band in bands) + RAIL_EPS:
        raise GrammarError(
            f"opening {opening.id}: head at {z1} rises above the walls of wing "
            f"{wing.id}")
    # A step in the wall plane across the aperture is only survivable if the
    # assembly's own reveal is deep enough to bridge it: a door crossing a 60 mm
    # plinth projection still reads, the same door crossing a 220 mm cornice
    # leaves its head hanging in front of the wall.
    insets = [value for band in crossed
              for value in (band.inset_low, band.inset_high)]
    step = max(insets) - min(insets)
    if step > opening.reveal + RAIL_EPS:
        raise GrammarError(
            f"opening {opening.id}: crosses a course boundary it cannot fit "
            f"inside -- courses "
            f"{sorted({band.course.kind for band in crossed})} of wing "
            f"{wing.id} step {step} in depth, more than its "
            f"{opening.reveal} reveal")
    if mirror_y and opening.elevation in ("front", "back"):
        oy0 = max(oy0, 0.0)
        if oy1 - oy0 <= RAIL_EPS:
            return None
    return _Hole(opening, oy0, oy1, z0, z1)


def _greedy_rects(solid, columns, rows):
    """Merge a marked sub-grid back into as few rectangles as it allows.

    Without this an opening would put the per-cell face count back on the one
    panel it pierces: two windows in one storey are five rectangles, not
    fifteen cells.
    """
    used = set()
    rectangles = []
    for row in range(rows):
        column = 0
        while column < columns:
            if (column, row) in used or not solid[(column, row)]:
                column += 1
                continue
            last_column = column
            while (last_column + 1 < columns and solid[(last_column + 1, row)]
                   and (last_column + 1, row) not in used):
                last_column += 1
            last_row = row
            while last_row + 1 < rows and all(
                    solid[(each, last_row + 1)] and (each, last_row + 1) not in used
                    for each in range(column, last_column + 1)):
                last_row += 1
            for each in range(column, last_column + 1):
                for level in range(row, last_row + 1):
                    used.add((each, level))
            rectangles.append((column, last_column + 1, row, last_row + 1))
            column = last_column + 1
    return rectangles


# --------------------------------------------------------------------------
# gable caps
# --------------------------------------------------------------------------

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


def _gable_caps(recipe, wing, top_loop, eave, mirror_x, mirror_y):
    """The triangular wall above the eave, shaped by the roof over this wing.

    The cap sits on the TOP BAND's footprint rather than on the wing rectangle:
    a projecting cornice moves the surface the cap has to land on, and a cap
    that missed it would leave the top of the building open along a 90 mm strip.
    """
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
        x0 = quantise(min(x for x, _ in top_loop))
        x1 = quantise(max(x for x, _ in top_loop))
        y0 = quantise(min(y for _, y in top_loop))
        y1 = quantise(max(y for _, y in top_loop))
        apex = quantise(eave + section.rise)
        if section.ridge_axis == "Y":
            # Ridge along the street: the triangle faces the returns and the
            # slopes present to the street, so the street semantic rides the
            # sloping sides.
            ridge_a = quantise((x0 + x1) / 2.0 + section.ridge_offset)
            profile = [(x0, eave), (x1, eave), (ridge_a, apex)]
            if mirror_x:
                profile = _clip_positive(profile)
                if len(profile) < 3:
                    continue
            caps.append((profile, "Y", y0, y1,
                         course.return_semantic or course.semantic,
                         course.semantic, eave, mirror_y and y0 <= RAIL_EPS,
                         mirror_x))
        else:
            ridge_a = quantise(wing.lane_offset + section.ridge_offset)
            profile = [(y0, eave), (y1, eave), (ridge_a, apex)]
            if mirror_y:
                profile = _clip_positive(profile)
                if len(profile) < 3:
                    continue
            caps.append((profile, "X", x0, x1,
                         course.semantic,
                         course.return_semantic or course.semantic, eave,
                         mirror_x and x0 <= RAIL_EPS, mirror_y))
    return caps


# --------------------------------------------------------------------------
# the sweep
# --------------------------------------------------------------------------

def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _in_mirror_plane(a, b, axis):
    index = 0 if axis == "X" else 1
    return abs(a[index]) <= RAIL_EPS and abs(b[index]) <= RAIL_EPS


def _edge_semantic(course, direction):
    """Street face or return, decided by which way the edge looks.

    ``return_semantic`` exists so a course can carry whitewash on the street
    and rough limestone on the corner, and in a sweep the only thing that can
    tell them apart is the edge's own outward normal.
    """
    outward = _outward(direction)
    if outward[0] < -0.5:
        return course.semantic
    return course.return_semantic or course.semantic


def _sweep_edge(builder, band, low_loop, high_loop, index, holes, mirror_axes):
    """One (plan edge x band) quad, subdivided only if an aperture pierces it."""
    count = len(low_loop)
    low_a, low_b = low_loop[index], low_loop[(index + 1) % count]
    high_a, high_b = high_loop[index], high_loop[(index + 1) % count]
    for axis in mirror_axes:
        if _in_mirror_plane(low_a, low_b, axis) and _in_mirror_plane(high_a, high_b, axis):
            return  # the cut through the mirror plane carries no face
    direction = _unit((low_b[0] - low_a[0], low_b[1] - low_a[1]))
    if direction is None:
        return
    semantic = _edge_semantic(band.course, direction)

    def at(s, t):
        """A point on the quad in (along-edge, up-band) parameters."""
        a = _lerp(low_a, high_a, t)
        b = _lerp(low_b, high_b, t)
        x, y = _lerp(a, b, s)
        return (x, y, band.z0 + (band.z1 - band.z0) * t)

    # Match the edge by its outward normal; the opening-local frame then makes
    # the same reveal assembly meet front, return and rear walls alike.
    applicable = []
    outward = _outward(direction)
    edge_elevation = ("front" if outward[0] < -0.5 else
                      "back" if outward[0] > 0.5 else
                      "left" if outward[1] < -0.5 else "right")
    along_axis = 1 if edge_elevation in ("front", "back") else 0
    if band.z1 - band.z0 > RAIL_EPS:
        span_low, span_high = sorted((low_a[along_axis], low_b[along_axis]))
        for hole in holes:
            if hole.opening.elevation == edge_elevation \
                    and hole.a0 >= span_low - RAIL_EPS and hole.a1 <= span_high + RAIL_EPS \
                    and hole.z1 > band.z0 + RAIL_EPS and hole.z0 < band.z1 - RAIL_EPS:
                applicable.append(hole)
    if not applicable:
        builder.add_face([at(0.0, 0.0), at(1.0, 0.0), at(1.0, 1.0), at(0.0, 1.0)],
                         semantic)
        return

    # Subdivide the panel -- and only this panel -- on the aperture rails, then
    # merge the surviving cells greedily so the wall does not become a grid.
    y_rails = _dedupe([low_a[along_axis], low_b[along_axis]]
                      + [value for hole in applicable for value in (hole.a0, hole.a1)])
    z_rails = _dedupe([band.z0, band.z1]
                      + [min(max(value, band.z0), band.z1)
                         for hole in applicable for value in (hole.z0, hole.z1)])
    forward = low_b[along_axis] > low_a[along_axis]
    solid = {}
    for column in range(len(y_rails) - 1):
        cy = (y_rails[column] + y_rails[column + 1]) / 2.0
        for row in range(len(z_rails) - 1):
            cz = (z_rails[row] + z_rails[row + 1]) / 2.0
            solid[(column, row)] = not any(
                hole.a0 < cy < hole.a1 and hole.z0 < cz < hole.z1
                for hole in applicable)
    span = y_rails[-1] - y_rails[0]
    height = band.z1 - band.z0

    def parameters(column, row):
        y = y_rails[column]
        s = (y - y_rails[0]) / span if forward else (y_rails[-1] - y) / span
        return s, (z_rails[row] - band.z0) / height

    for c0, c1, r0, r1 in _greedy_rects(solid, len(y_rails) - 1, len(z_rails) - 1):
        s0, t0 = parameters(c0, r0)
        s1, t1 = parameters(c1, r1)
        if not forward:
            s0, s1 = s1, s0
        builder.add_face([at(s0, t0), at(s1, t0), at(s1, t1), at(s0, t1)],
                         semantic)


def _add_cap(builder, loop, z, semantic, *, upward):
    points = [(x, y, z) for x, y in loop]
    builder.add_face(points if upward else list(reversed(points)), semantic)


def _pier_ring(builder, plain, piered, z, semantic):
    """Cap the plan difference where the pier stops, one hexagon per corner.

    The piered loop only ADDS vertices, so the two loops agree everywhere else
    and the difference is exactly the corner runs.  Emitting the ring as a
    hexagon rather than as an annulus is what keeps it one face.
    """
    plain_set = {(quantise(x), quantise(y)) for x, y in plain}
    count = len(piered)
    index = 0
    while index < count:
        point = (quantise(piered[index][0]), quantise(piered[index][1]))
        if point in plain_set:
            index += 1
            continue
        start = index - 1
        end = index
        while end + 1 < count and (quantise(piered[end + 1][0]),
                                   quantise(piered[end + 1][1])) not in plain_set:
            end += 1
        run = [piered[position % count] for position in range(start, end + 2)]
        corner = _corner_between(plain, run[0], run[-1])
        if corner is not None:
            builder.add_face([(x, y, z) for x, y in run] + [(corner[0], corner[1], z)],
                             semantic)
        index = end + 1


def _corner_between(plain, before, after):
    """The plain-outline vertex the pier run replaced, found by intersection."""
    for index in range(len(plain)):
        current = plain[index]
        if abs(current[0] - before[0]) + abs(current[1] - before[1]) < RAIL_EPS:
            continue
        # `before` and `after` both lie ON the plain outline's edges either side
        # of the corner, so the corner is the plain vertex nearest to both.
    best = None
    for vertex in plain:
        score = math.dist(vertex, before) + math.dist(vertex, after)
        if best is None or score < best[0]:
            best = (score, vertex)
    return best[1] if best else None


def build_body(recipe):
    """Resolve a recipe's wings and courses into the single ``body`` record."""
    mirror_y = "Y" in recipe.mirror_axes
    mirror_x = "X" in recipe.mirror_axes
    mirror_axes = tuple(axis for axis, on in (("X", mirror_x), ("Y", mirror_y)) if on)

    if recipe.outline:
        loops = [[(quantise(x), quantise(y)) for x, y in recipe.outline]]
    else:
        rects = [rect for rect in
                 (_wing_rect(wing, mirror_x, mirror_y) for wing in recipe.wings)
                 if rect is not None]
        if not rects:
            raise GrammarError(f"recipe {recipe.id}: no wing survives the build")
        loops = _trace_loops(rects)
    for loop in loops:
        if _signed_area_2d(loop) < 0.0:
            raise GrammarError(
                f"recipe {recipe.id}: the plan outline encloses a courtyard, "
                "which the sweep has no vocabulary for")

    bands = _shared_stack(recipe)
    reference = recipe.wings[0]
    pier = getattr(reference, "pier", None)
    through = None
    if pier is not None and pier.through is not None:
        kinds = [band.course.kind for band in bands]
        if pier.through not in kinds:
            raise GrammarError(
                f"wing {reference.id}: pier runs through course "
                f"{pier.through!r}, which the wing does not have")
        through = max(index for index, kind in enumerate(kinds)
                      if kind == pier.through)

    holes = []
    cut = []
    for opening in recipe.openings:
        hole = _opening_hole(recipe, opening, bands, mirror_y)
        if hole is not None:
            holes.append(hole)
            cut.append(opening.role)

    builder = MeshBuilder(f"{recipe.id}_body")
    top_loops = []
    for plain in loops:
        piered = _apply_pier(plain, pier) if pier is not None else plain
        previous_base = None
        for index, band in enumerate(bands):
            base = piered if (through is None or index <= through) else plain
            if previous_base is not None and base is not previous_base:
                # The pier stops here: cap the plan difference before carrying on.
                _pier_ring(builder, _offset(plain, -band.inset_low, mirror_axes),
                           _offset(previous_base, -band.inset_low, mirror_axes), band.z0,
                           band.course.semantic)
            low = _offset(base, -band.inset_low, mirror_axes)
            high = _offset(base, -band.inset_high, mirror_axes)
            for edge in range(len(base)):
                _sweep_edge(builder, band, low, high, edge, holes, mirror_axes)
            if index == 0:
                _add_cap(builder, low, band.z0, band.course.semantic, upward=False)
            previous_base = base
        final = bands[-1]
        top_loops.append(_offset(
            piered if (through is None or through >= len(bands) - 1) else plain,
            -final.inset_high, mirror_axes))

    eave = reference.eave_z
    caps = []
    for wing in recipe.wings:
        caps.extend(_gable_caps(recipe, wing, top_loops[0], eave,
                                mirror_x, mirror_y))
    if not caps:
        for loop in top_loops:
            _add_cap(builder, loop, bands[-1].z1, bands[-1].course.semantic,
                     upward=True)

    for (profile, axis, low, high, cap_semantic, side_semantic, cap_eave,
         skip_cap_low, skip_side_at_zero) in caps:
        _add_prism(builder, profile, axis, low, high, cap_semantic,
                   side_semantic, skip_z=cap_eave, skip_cap_low=skip_cap_low,
                   skip_side_at_zero=skip_side_at_zero)

    origin = (min(x for loop in loops for x, _ in loop), 0.0, 0.0)
    modifiers = ((ModifierSpec("MIRROR", axes=mirror_axes),) if mirror_axes else ())
    metadata = {
        "wings": [wing.id for wing in recipe.wings],
        "eaveZ": {wing.id: wing.eave_z for wing in recipe.wings},
        "openings": cut,
    }
    return builder.record("body", origin=origin, parent_role=None,
                          modifiers=modifiers, metadata=metadata)
