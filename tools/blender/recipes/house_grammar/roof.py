"""The roof builder: every section of a building fused into one slab.

The vocabulary is `Exterior.gable_roof()` generalised.  That routine established
what a St. Maria roof *is*: a ridge parallel to the street, small overhangs that
clear the masonry on every side, a roof mass that is independent of the wall
mass, and a ``ridge_offset`` that slides the peak across the span without
scaling either slope.  Everything here keeps those four properties and adds the
three things a terrace needs that a single prism cannot express -- a real
thickness, a stepped eave, and junctions between sections.

**Why a height field rather than solid CSG.**  A valley is the one junction the
prism form cannot state: where a cross gable meets a gable at right angles the
lower surface has to be clipped against the higher one along a line that is
diagonal in plan.  Boolean CSG in pure Python would be a second, far larger
piece of machinery to keep deterministic.  Instead every section contributes a
piecewise-linear surface ``z(x, y)`` and the roof is their upper envelope:

    max(...)  clips the lower section against the higher one  -> valley
    max(...)  of two identical sections is that same surface  -> continuous run
    the union of footprints is the domain                     -> one skin

Fusion is therefore an arithmetic property of the envelope rather than a
sequence of pairwise operations, which is what makes it order-independent: the
result does not depend on which section is resolved against which first.  The
only ordering that survives is the tie-break for a face's material semantic,
which is recipe order.

The envelope is sampled on the grid of every section's own break lines --
footprint edges, ridge lines, hip insets -- so each straight crease lands on a
cell edge exactly.  The one crease that does not is the valley, which is
diagonal; each cell picks the diagonal that reproduces the true surface at its
centre, so a symmetric valley is exact and an asymmetric one is a chord.

The slab is then closed: envelope on top, the same surface dropped by
``thickness`` underneath as the soffit, and a vertical fascia everywhere the
domain ends.  A closed solid is what makes "no internal faces" checkable rather
than asserted -- every edge is shared by exactly two faces.
"""

from __future__ import annotations

from .records import GrammarError, MeshBuilder, ModifierSpec, quantise

# Break lines closer together than this collapse onto one another.  A centimetre
# is well under what the 27.4 px/m exterior camera can resolve, and the floor
# matters: two rails a micrometre apart would spawn a cell whose triangles fall
# under `records.MIN_FACE_AREA` and fail validation as degenerate.
RAIL_TOLERANCE = 0.01

# Where one section's edge falls inside another's footprint the envelope has a
# genuine vertical step -- the higher roof's eave passes over the lower roof --
# and a welded height field cannot hold a vertical face.  Rails a collar away
# from such an edge confine that step to a 5 cm ramp instead of letting it lean
# across a whole cell.  Five centimetres is 1.4 px at the exterior camera's
# 27.4 px/m, so the ramp is sub-pixel and the eave reads as the step it is.
COLLAR = 0.05

# Slack for "is this point inside that footprint".  A point sitting exactly on a
# shared edge must belong to both sections, or the envelope would step at the
# seam between two sections that are meant to run continuously.
INSIDE_EPSILON = 1e-9


class _Section:
    """One roof section reduced to an envelope function over its own footprint.

    The section already knows its wing: the footprint here is the wing's plan
    expanded by ``overhang`` on all four sides, which is `gable_roof()`'s
    masonry-clearing overhang written once for every profile.
    """

    def __init__(self, spec, wing, order):
        self.spec = spec
        self.wing = wing
        self.order = order
        self.profile = spec.profile
        self.axis = spec.ridge_axis
        self.semantic = spec.semantic
        self.thickness = spec.thickness
        over = spec.overhang
        x0, x1 = wing.x_span()
        y0, y1 = wing.y_span()
        self.x0, self.x1 = quantise(x0 - over), quantise(x1 + over)
        self.y0, self.y1 = quantise(y0 - over), quantise(y1 + over)
        self.eave_z = wing.eave_z
        self.rise = spec.rise
        self.ridge_z = quantise(self.eave_z + spec.rise)
        self.step = spec.eave_step
        self.fraction = spec.hip_fraction

        # The span is the direction the slopes run in; the ridge runs along the
        # other one.  ridge_axis "Y" -- the street-parallel ridge of every
        # authored Praca roof -- therefore slopes across X, into depth.
        if self.axis == "Y":
            self.s0, self.s1 = self.x0, self.x1
            self.a0, self.a1 = self.y0, self.y1
        else:
            self.s0, self.s1 = self.y0, self.y1
            self.a0, self.a1 = self.x0, self.x1

        if self.profile == "lean_to":
            # A single slope: the ridge sits on an edge rather than inside the
            # span.  A negative ridge_offset flips which edge, because that is
            # the only free choice a lean-to has.
            self.ridge_s = self.s0 if spec.ridge_offset < 0.0 else self.s1
        else:
            self.ridge_s = quantise((self.s0 + self.s1) / 2.0 + spec.ridge_offset)
            if not self.s0 < self.ridge_s < self.s1:
                raise GrammarError(
                    f"roof {spec.wing}: ridge_offset {spec.ridge_offset} puts the "
                    "ridge outside the span")

        # A hipped end runs at the pitch of the steeper of the two slopes, so
        # the hip line reads as a true mitre rather than as a separate roof
        # stuck on the end.  The inset can never eat more than half the ridge.
        runs = [r for r in (self.ridge_s - self.s0, self.s1 - self.ridge_s) if r > 0.0]
        self.inset = min(min(runs), (self.a1 - self.a0) / 2.0)

    # -- geometry ---------------------------------------------------------
    def contains(self, x, y):
        return (self.x0 - INSIDE_EPSILON <= x <= self.x1 + INSIDE_EPSILON
                and self.y0 - INSIDE_EPSILON <= y <= self.y1 + INSIDE_EPSILON)

    def _eave_z(self, side, x, y):
        """Height of the eave line ``side`` (0 = low span edge, 1 = high).

        ``eave_step`` drops the eave on the +Y end and leaves the ridge alone,
        so a terrace can walk down a slope without its roofline breaking into
        separate prisms.  With a street-parallel ridge that tilts both slopes
        along their length; with a ridge running into depth the two eaves simply
        sit at different heights.
        """
        if self.step == 0.0:
            return self.eave_z
        if self.axis == "Y":
            span = self.y1 - self.y0
            return self.eave_z - self.step * (y - self.y0) / span
        return self.eave_z - (self.step if side else 0.0)

    def _slope_z(self, x, y):
        """The two-slope cross-section, before any end is hipped."""
        s = x if self.axis == "Y" else y
        if self.profile == "lean_to":
            far = self.s1 if self.ridge_s == self.s0 else self.s0
            base = self._eave_z(0 if far == self.s0 else 1, x, y)
            t = (s - far) / (self.ridge_s - far)
            return base + (self.ridge_z - base) * t
        if s <= self.ridge_s:
            base = self._eave_z(0, x, y)
            t = (s - self.s0) / (self.ridge_s - self.s0)
        else:
            base = self._eave_z(1, x, y)
            t = (self.s1 - s) / (self.s1 - self.ridge_s)
        return base + (self.ridge_z - base) * t

    def _end_z(self, x, y):
        """The hipped ends, as planes rising from the two ends of the ridge.

        ``None`` when the profile keeps vertical gable ends.  A half hip is the
        same plane lifted by ``hip_fraction`` of the rise, which is precisely
        what a jerkinhead is: the gable stands until that height and the hip
        takes over above it.
        """
        if self.profile not in ("hip", "half_hip"):
            return None
        a = y if self.axis == "Y" else x
        lift = self.fraction * self.rise if self.profile == "half_hip" else 0.0
        # A hipped end springs from the eave line it stands on.  With the ridge
        # running into depth both ends spring from the un-stepped height: the
        # step tilts the slopes, and letting it tilt the hips as well would
        # twist the mitre.
        base_low = self._eave_z(0, x, self.y0)
        base_high = self._eave_z(1 if self.axis == "Y" else 0, x, self.y1)
        low = base_low + lift + self.rise * (a - self.a0) / self.inset
        high = base_high + lift + self.rise * (self.a1 - a) / self.inset
        return min(low, high)

    def z(self, x, y):
        """Surface height at a plan point.  A roof is the LOWER envelope of the
        planes rising from its own eaves -- that is what makes a hip a hip."""
        z = self._slope_z(x, y)
        end = self._end_z(x, y)
        if end is not None:
            z = min(z, end)
        return min(z, self.ridge_z)

    # -- book-keeping -----------------------------------------------------
    def rails(self):
        """The plan lines this section's creases lie on."""
        xs, ys = [self.x0, self.x1], [self.y0, self.y1]
        (xs if self.axis == "Y" else ys).append(self.ridge_s)
        if self.profile in ("hip", "half_hip"):
            shrink = self.inset
            if self.profile == "half_hip":
                shrink *= 1.0 - self.fraction
            ends = (self.a0 + shrink, self.a1 - shrink)
            (ys if self.axis == "Y" else xs).extend(ends)
        return xs, ys

    def ridge_length(self, floor_y):
        lo, hi = self.a0, self.a1
        if self.axis == "Y":
            lo = max(lo, floor_y)
        if self.profile == "hip":
            lo, hi = lo + self.inset, hi - self.inset
        elif self.profile == "half_hip":
            shrink = self.inset * (1.0 - self.fraction)
            lo, hi = lo + shrink, hi - shrink
        return max(0.0, hi - lo)


def _rails(values, floor=None):
    """Sorted, de-duplicated break lines, optionally clipped to a floor."""
    kept = []
    for value in sorted(quantise(v) for v in values):
        if floor is not None:
            if value < floor - RAIL_TOLERANCE:
                continue
            value = max(value, floor)
        if kept and value - kept[-1] < RAIL_TOLERANCE:
            continue
        kept.append(quantise(value))
    return kept


def build_roof(recipe):
    """Fuse every roof section of ``recipe`` into one ``roof`` record."""
    if not recipe.roof:
        raise GrammarError(f"recipe {recipe.id}: build_roof called with no sections")

    sections = [_Section(spec, recipe.wing(spec.wing), order)
                for order, spec in enumerate(recipe.roof)]

    mirrored = "Y" in recipe.mirror_axes
    floor_y = 0.0 if mirrored else None
    thickness = min(section.thickness for section in sections)

    xs, ys = [], []
    for section in sections:
        section_xs, section_ys = section.rails()
        xs.extend(section_xs)
        ys.extend(section_ys)
    for section in sections:
        for other in sections:
            if other is section:
                continue
            if (section.x1 <= other.x0 or section.x0 >= other.x1
                    or section.y1 <= other.y0 or section.y0 >= other.y1):
                continue
            for edge in (section.x0, section.x1):
                if other.x0 < edge < other.x1:
                    xs.extend((edge - COLLAR, edge + COLLAR))
            for edge in (section.y0, section.y1):
                if other.y0 < edge < other.y1:
                    ys.extend((edge - COLLAR, edge + COLLAR))
    if mirrored:
        ys.append(0.0)
    xs, ys = _rails(xs), _rails(ys, floor_y)
    if len(xs) < 2 or len(ys) < 2:
        raise GrammarError(f"recipe {recipe.id}: roof collapsed to nothing in plan")

    def envelope(x, y):
        """Roof surface at a point, resolving section overlaps as valleys.

        A higher section must not bridge an L's inside corner: the junction is
        a valley where both roof planes meet.  Outside an overlap this is the
        ordinary single-section surface.
        """
        candidates = []
        for section in sections:
            if not section.contains(x, y):
                continue
            candidates.append((section.z(x, y), section))
        if not candidates:
            return None, None
        # The lower surface is the physically open inside corner; selecting
        # the upper one was the source of the spurious joining plane.
        return min(candidates, key=lambda item: item[0])

    # Rasterise the domain once; cell membership is exact because every
    # footprint edge is a rail, so no cell is ever half covered.
    cells = {}
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx = (xs[i] + xs[i + 1]) / 2.0
            cy = (ys[j] + ys[j + 1]) / 2.0
            z, owner = envelope(cx, cy)
            if owner is None:
                continue
            cells[(i, j)] = (owner, z)
    if not cells:
        raise GrammarError(f"recipe {recipe.id}: roof covers no ground")

    corner_z = {}

    def top(i, j):
        if (i, j) not in corner_z:
            z, _ = envelope(xs[i], ys[j])
            corner_z[(i, j)] = quantise(z)
        return corner_z[(i, j)]

    builder = MeshBuilder(f"{recipe.id}_roof")

    for (i, j), (owner, centre_z) in sorted(cells.items()):
        x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
        z00, z10, z11, z01 = top(i, j), top(i + 1, j), top(i + 1, j + 1), top(i, j + 1)
        corners = [(x0, y0, z00), (x1, y0, z10), (x1, y1, z11), (x0, y1, z01)]
        # A straight roof plane does not need an internal diagonal.  Keeping
        # the cell as one quad is important in the authored studies: the
        # raster rails are construction aids, not visible topology.  Only a
        # genuinely bent envelope gets triangulated.
        planar = (z00 + z11 == z10 + z01
                  and abs(z00 - z10 - z01 + z11) <= 1e-6)
        if planar:
            surfaces = [corners]
        elif abs((z01 + z10) / 2.0 - centre_z) < abs((z00 + z11) / 2.0 - centre_z):
            surfaces = [[corners[index] for index in triangle]
                        for triangle in ((0, 1, 3), (1, 2, 3))]
        else:
            surfaces = [[corners[index] for index in triangle]
                        for triangle in ((0, 1, 2), (0, 2, 3))]
        for points in surfaces:
            builder.add_face(points, owner.semantic)
            # The soffit follows the same topology, so an eave reads as a
            # board with an underside rather than as a paper edge.
            drop = [(x, y, quantise(z - thickness)) for x, y, z in reversed(points)]
            builder.add_face(drop, owner.semantic)

        for side, neighbour in (("-x", (i - 1, j)), ("+x", (i + 1, j)),
                                ("-y", (i, j - 1)), ("+y", (i, j + 1))):
            if neighbour in cells:
                continue
            if side == "-y" and mirrored and abs(y0) < INSIDE_EPSILON:
                # The mirror plane is a cut, not a surface: emitting the cut
                # face would bury it inside the mirrored solid.
                continue
            if side in ("-x", "+x"):
                x = x0 if side == "-x" else x1
                za = top(i if side == "-x" else i + 1, j)
                zb = top(i if side == "-x" else i + 1, j + 1)
                rail = [(x, y0, quantise(za - thickness)), (x, y0, za),
                        (x, y1, zb), (x, y1, quantise(zb - thickness))]
                if side == "+x":
                    rail.reverse()
            else:
                y = y0 if side == "-y" else y1
                za = top(i, j if side == "-y" else j + 1)
                zb = top(i + 1, j if side == "-y" else j + 1)
                rail = [(x0, y, za), (x0, y, quantise(za - thickness)),
                        (x1, y, quantise(zb - thickness)), (x1, y, zb)]
                if side == "+y":
                    rail.reverse()
            builder.add_face(rail, owner.semantic)

    metadata = {
        "sections": {
            section.spec.wing: {
                "profile": section.profile,
                "ridgeZ": section.ridge_z,
                "eaveZ": section.eave_z,
            }
            for section in sections
        },
        "ridgeLength": quantise(sum(section.ridge_length(floor_y if mirrored else -1e9)
                                    for section in sections)),
    }
    modifiers = (ModifierSpec("MIRROR", axes=("Y",)),) if mirrored else ()

    # The body and roof share the authored plan's origin.  A union outline can
    # differ from every wing setback, so deriving this from wings would let a
    # T/L roof drift relative to its body.
    plan_origin_x = (min(x for x, _ in recipe.outline)
                     if recipe.outline
                     else min(wing.setback for wing in recipe.wings))
    origin = (quantise(plan_origin_x), 0.0, 0.0)
    return builder.record("roof", origin=origin, parent_role="body",
                          modifiers=modifiers, metadata=metadata)
