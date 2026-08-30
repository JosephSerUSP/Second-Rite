"""Blender-free meshing for :mod:`tree_generator` skeletons.

The skeleton generator is deliberately independent of Blender, but until now
the only thing able to *mesh* a skeleton lived inside a Blender recipe and
relied on the Skin modifier.  That coupled every consumer -- recipes, the live
bridge, any future exporter -- to an interactive Blender session, and left the
mesh itself untestable.

This module closes that gap.  It turns a skeleton into plain vertex/face/UV
lists using node rings carried along the branch graph by parallel transport,
so a fork shares its parent's ring instead of stacking two capped cones at the
same point.  Blender is only ever needed to *receive* the result.
"""
from __future__ import annotations

import math

from tree_generator import Skeleton


def _add(a, b): return tuple(x + y for x, y in zip(a, b))
def _sub(a, b): return tuple(x - y for x, y in zip(a, b))
def _scale(a, s): return tuple(x * s for x in a)
def _dot(a, b): return sum(x * y for x, y in zip(a, b))
def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _length(a): return math.sqrt(_dot(a, a))
def _unit(a):
    n = _length(a)
    return (0.0, 0.0, 1.0) if n < 1e-9 else _scale(a, 1.0 / n)


def _rotate(vector, axis, cos_a, sin_a):
    """Rodrigues rotation; used to carry a reference vector across a joint."""
    return _add(_add(_scale(vector, cos_a), _scale(_cross(axis, vector), sin_a)),
                _scale(axis, _dot(axis, vector) * (1.0 - cos_a)))


def _transport(reference, from_dir, to_dir):
    """Move ``reference`` from one branch direction to the next.

    Rotating by the minimal arc keeps consecutive rings aligned, which is what
    stops a straight run from twisting and a fork from shearing.
    """
    axis = _cross(from_dir, to_dir)
    sin_a = _length(axis)
    cos_a = max(-1.0, min(1.0, _dot(from_dir, to_dir)))
    if sin_a < 1e-9:
        return reference if cos_a > 0 else _scale(reference, -1.0)
    return _unit(_rotate(reference, _scale(axis, 1.0 / sin_a), cos_a, sin_a))


def _ring(centre, direction, reference, radius, sides):
    binormal = _unit(_cross(direction, reference))
    normal = _unit(_cross(binormal, direction))
    points = []
    for side in range(sides):
        angle = math.tau * side / sides
        offset = _add(_scale(normal, math.cos(angle) * radius),
                      _scale(binormal, math.sin(angle) * radius))
        points.append(_add(centre, offset))
    return points


def card_corners(centre, across, along, width, height):
    """The four corners of one alpha card, in UV order.

    Shared with the grass scatter: a card is a card whether it hangs off a
    branch or stands on the ground, and only the placement rule differs.
    """
    half_u = _scale(_unit(across), width * .5)
    half_v = _scale(_unit(along), height * .5)
    return (_sub(_sub(centre, half_u), half_v),
            _sub(_add(centre, half_u), half_v),
            _add(_add(centre, half_u), half_v),
            _add(_sub(centre, half_u), half_v))


def atlas_uvs(columns=4, cell=2):
    """Corner UVs selecting one column of a horizontal sprite atlas."""
    u0, u1 = cell / columns, (cell + 1) / columns
    return ((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0))


def branch_mesh(skeleton: Skeleton, *, sides: int = 6, origin=(0.0, 0.0, 0.0),
                minimum_radius: float = .018):
    """Mesh the woody graph as one connected tube network.

    Every skeleton node owns exactly one ring.  A segment bridges its parent's
    ring to its own, so a fork splits a shared sleeve rather than introducing a
    second capped cone -- the fault that made the earlier per-segment builder
    read as a pile of funnels.
    """
    if sides < 3:
        raise ValueError("a branch tube needs at least three sides")
    segments = skeleton.segments
    if not segments:
        raise ValueError("cannot mesh an empty skeleton")
    by_index = {segment.index: segment for segment in segments}
    children = {}
    for segment in segments:
        children.setdefault(segment.parent, []).append(segment.index)

    root = segments[0]
    root_dir = _unit(_sub(root.end, root.start))
    seed = (0.0, 1.0, 0.0) if abs(root_dir[1]) < .9 else (1.0, 0.0, 0.0)
    # The ground ring is the one place a basal flare belongs.  Without it
    # the root ring equals the first node ring and the bole meets the
    # paving as a cut pipe.
    flare = getattr(skeleton.spec, "root_flare", 1.0)
    frames = {None: (root.start, root_dir, _unit(_cross(_cross(root_dir, seed), root_dir)),
                     max(minimum_radius, root.radius * flare))}

    verts, faces = [], []
    ring_base = {}

    def emit_ring(key, centre, direction, reference, radius):
        base = len(verts)
        verts.extend(_add(point, origin) for point in
                     _ring(centre, direction, reference, radius, sides))
        ring_base[key] = base
        return base

    emit_ring(None, *frames[None])
    order = sorted(by_index)
    for index in order:
        segment = by_index[index]
        parent_key = segment.parent
        if parent_key not in frames:
            raise ValueError(f"segment {index} references an unmeshed parent")
        _centre, parent_dir, parent_reference, _radius = frames[parent_key]
        direction = _unit(_sub(segment.end, segment.start))
        reference = _transport(parent_reference, parent_dir, direction)
        radius = max(minimum_radius, segment.radius * (.78 if segment.foliage else .9))
        frames[index] = (segment.end, direction, reference, radius)
        base = emit_ring(index, segment.end, direction, reference, radius)
        parent_base = ring_base[parent_key]
        for side in range(sides):
            nxt = (side + 1) % sides
            faces.append((parent_base + side, parent_base + nxt, base + nxt, base + side))

    # Cap the root and every tip so the tube is closed; interior nodes stay
    # open because a cap there would be geometry buried inside the trunk.
    faces.append(tuple(reversed(range(ring_base[None], ring_base[None] + sides))))
    for index in order:
        if not children.get(index):
            base = ring_base[index]
            faces.append(tuple(range(base, base + sides)))
    return verts, faces


#: A carrier may hold a short chain of sprays.  Cards used to be one per
#: carrier and carriers are skeleton segments, so crown coverage was capped
#: by the segment budget: a wide crown could not be filled at all, only
#: stretched.  Chaining outward decouples coverage from segment count.
MAX_SPRAYS_PER_CARRIER = 4
#: How far each chain link steps outward, as a fraction of spray length.
SPRAY_CHAIN_STEP = .52
#: Vertex ceiling for one authored card mesh, matching the live bridge's
#: per-request limit so a generated crown is always placeable.
MAX_CARD_VERTICES = 1024


def sprays_per_carrier(spec, carriers, crossings=2):
    """How many sprays each carrier chains outward to close the crown.

    A wider crown needs foliage further from the trunk, which is a count
    of sprays along the reach -- never a bigger spray.  The result is
    clamped so the finished mesh still fits one bridge request.
    """
    if carriers <= 0:
        return 1
    reach = max(.1, spec.crown_radius) / max(.05, spec.spray_length * .55)
    count = max(1, min(MAX_SPRAYS_PER_CARRIER, int(round(reach))))
    while count > 1 and carriers * count * crossings * 4 > MAX_CARD_VERTICES:
        count -= 1
    return count


def foliage_mesh(skeleton: Skeleton, *, lod: str = "low", origin=(0.0, 0.0, 0.0),
                 atlas_columns: int = 4, atlas_cell: int = 2):
    """Crossed alpha branch-spray cards, with the atlas UVs the sprites need.

    Returns ``(vertices, faces, uvs)`` where ``uvs`` is one coordinate per face
    corner, in face order -- the layout Blender's loop-indexed UV layer wants.
    """
    spec = skeleton.spec
    by_index = {segment.index: segment for segment in skeleton.segments}
    # Always a crossed pair.  A single plane per carrier disappears edge-on,
    # which read as a sparse, gap-ridden crown rather than as a cheap one;
    # the second quad costs four vertices and fixes it from every angle.
    crossings = 2
    verts, faces, uvs = [], [], []
    corner_uvs = atlas_uvs(atlas_columns, atlas_cell)
    chain = sprays_per_carrier(spec, len(skeleton.foliage_carriers), crossings)
    for n, carrier in enumerate(skeleton.foliage_carriers):
        segment = by_index[carrier.segment_index]
        a = _add(segment.start, origin)
        b = _add(segment.end, origin)
        tangent = _unit(_sub(b, a))
        helper = (0.0, 0.0, 1.0) if abs(tangent[2]) < .9 else (0.0, 1.0, 0.0)
        base_u = _unit(_cross(tangent, helper))
        base_n = _unit(_cross(tangent, base_u))
        axis = _unit(_add(_scale(base_u, math.cos(carrier.roll_radians)),
                          _scale(base_n, math.sin(carrier.roll_radians))))
        carrier_length = _length(_sub(b, a))
        # Sprays chain outward along the crown radius, so a wider crown is
        # filled by reaching further rather than by inflating each card.
        radial = _unit((segment.end[0], segment.end[1], 0.0))
        if _length((segment.end[0], segment.end[1], 0.0)) < 1e-6:
            radial = axis
        for link in range(chain):
            variation = .90 + ((n * 37 + link * 53 + spec.seed * 17) % 23) / 100.0
            # Spray extent is absolute, in metres.  Deriving it from crown
            # radius made a wider crown grow BIGGER LEAVES instead of more of
            # them, which breaks apparent scale as soon as the tree is close
            # to camera.  Crown coverage is a budget question, not a size one.
            height = max(spec.spray_length, carrier_length * 1.8) * variation
            width = max(.52, height * .74)
            # The sprite stem starts on the supporting branch and most of the
            # image grows past its endpoint; centring cards on short twigs is
            # what left the earlier crowns pinched and bald.
            base_point = _sub(a, _scale(tangent, min(.10, height * .06)))
            centre = _add(_add(base_point, _scale(tangent, height * .5)), (0.0, 0.0, .04))
            if link:
                # Later links step outward along the crown radius, staggered
                # along the branch so a chain reads as a limb of foliage rather
                # than as one card repeated.
                reach = link * spec.spray_length * SPRAY_CHAIN_STEP
                centre = _add(centre, _scale(radial, reach))
                centre = _add(centre, _scale(tangent, (link % 2) * height * .18))
                # Keep the chain inside the authored crown.  Stepping outward
                # without a bound walks foliage out of its own envelope: on a
                # tree the vertex budget clamped the chain before that showed,
                # but a shrub's short sprays permit a long chain and it ballooned
                # to roughly three times the authored crown radius.
                span = math.hypot(centre[0], centre[1])
                if span > spec.crown_radius:
                    pull = spec.crown_radius / span
                    centre = (centre[0] * pull, centre[1] * pull, centre[2])
            for cross in range(crossings):
                u = axis if not cross else _unit(_cross(tangent, axis))
                base = len(verts)
                verts.extend(card_corners(centre, u, tangent, width, height))
                faces.append((base, base + 1, base + 2, base + 3))
                uvs.extend(corner_uvs)
    return verts, faces, uvs
