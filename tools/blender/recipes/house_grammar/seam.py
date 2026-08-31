"""The one repair the grammar is allowed to make to owner-authored topology.

The defect, the constants and every refusal case are specified in
`docs/design/st-maria-seam-defect.md`, which was written from measurements of
`st_maria_praca.blend` BEFORE this module existed. Read it first; this file
implements that document and adds nothing to it.

In one sentence: a single vertex dragged a few centimetres off the seam its
neighbours agree on, so Blender's Mirror duplicates it instead of welding it
and opens a notch. The repair pulls that vertex back onto the seam coordinate,
on that axis only.

The hard part is not the repair. It is refusing everything that merely
resembles it -- a uniformly drifted seam, a deliberate step, an interior
vertex, a loop that never agreed on a coordinate. A normalizer that repairs
those passes every positive test while quietly reshaping the buildings it was
meant to compare against, which is why `test_house_grammar_seam.py` asserts the
refusals first and the repairs second.
"""

from __future__ import annotations

# Vertices within this of the mirror plane are candidates for the seam loop.
# Anything further out is the body of the building.
COHORT_BAND = 0.25
# The largest displacement treated as a slip. Both measured instances are
# 0.07 m; a bay, a set-back or a buttress is metres away, and no repair may
# ever move one.
MAX_PULL = 0.10
# A seam is an edge loop, not a point. A cohort that cannot put this many
# vertices on one coordinate has no seam to speak of.
MIN_COHORT = 3
# Above this share of the cohort, the "defect" is a shape and its author meant
# it. There is no correct coordinate to pull a majority towards.
MAX_DEFECT_FRACTION = 0.25
# Blender's own merge threshold on these objects. Two coordinates closer than
# this are the same coordinate.
WELD_TOL = 1e-3


class SeamRefusal(Exception):
    """Raised only by `normalise(..., strict=True)`, to make a refusal loud."""


def edges_from_faces(faces):
    """Undirected edge set of a face list, as frozensets of index pairs."""
    edges = set()
    for face in faces:
        for position in range(len(face)):
            edges.add(frozenset((face[position], face[(position + 1) % len(face)])))
    return edges


def _neighbours(edges, count):
    table = {index: set() for index in range(count)}
    for edge in edges:
        a, b = tuple(edge)
        table[a].add(b)
        table[b].add(a)
    return table


def seam_coordinate(coordinates):
    """The coordinate a cohort agrees on, or None when it agrees on none.

    Deliberately the MODE of what the vertices actually do, never the plane the
    modifier nominates. `ARCH_west_house.006` has no vertex at all on its
    nominal plane -- its whole loop is drifted 1.7 mm -- and keying on the plane
    would flag the entire loop and "repair" the building by dragging its seam
    sideways.
    """
    clusters = []
    for value in sorted(coordinates):
        for cluster in clusters:
            if abs(cluster[0] - value) <= WELD_TOL:
                cluster.append(value)
                break
        else:
            clusters.append([value])
    if not clusters:
        return None
    # Ties break towards the lower coordinate so the answer is deterministic;
    # a tie means the cohort is split down the middle, which the minority rule
    # below rejects anyway.
    best = max(clusters, key=lambda cluster: (len(cluster), -cluster[0]))
    if len(best) < MIN_COHORT:
        return None
    return sum(best) / len(best)


def find_defects(vertices, faces, axis, plane):
    """Every vertex the documented predicate names, with its repair.

    Returns a list of ``{"vertex", "axis", "from", "to", "offset"}``. An empty
    list is the ordinary case and is not an error: most seams are clean.
    """
    if axis not in (0, 1, 2):
        raise ValueError(f"axis must be 0, 1 or 2, got {axis!r}")
    cohort = [index for index, vertex in enumerate(vertices)
              if abs(vertex[axis] - plane) <= COHORT_BAND]
    if len(cohort) < MIN_COHORT:
        return []
    seam = seam_coordinate([vertices[index][axis] for index in cohort])
    if seam is None:
        return []
    on_seam = {index for index in cohort
               if abs(vertices[index][axis] - seam) <= WELD_TOL}
    neighbours = _neighbours(edges_from_faces(faces), len(vertices))
    candidates = []
    for index in cohort:
        offset = vertices[index][axis] - seam
        if abs(offset) <= WELD_TOL:
            continue
        if abs(offset) > MAX_PULL:
            # A step in the building, not a slip. Never touched, and never
            # counted towards the minority rule either -- a building with two
            # deliberate bays must not thereby lose its one real repair.
            continue
        if not (neighbours[index] & on_seam):
            # An interior vertex that merely happens to sit in the band. It is
            # not part of the loop, so there is nothing for it to be off.
            continue
        candidates.append({"vertex": index, "axis": axis,
                           "from": vertices[index][axis], "to": seam,
                           "offset": offset})
    if not candidates:
        return []
    if len(candidates) > MAX_DEFECT_FRACTION * len(cohort):
        return []
    return candidates


def normalise(vertices, faces, mirror_axes, planes, *, strict=False):
    """Apply the documented repair, returning new vertices and a report.

    ``mirror_axes`` and ``planes`` are parallel sequences: only an axis carrying
    a Mirror modifier has a seam, so an axis absent from them is never touched.
    With ``strict`` the call raises `SeamRefusal` when nothing was repaired,
    which is how conformance asks for a repair it believes must exist.
    """
    moved = [list(vertex) for vertex in vertices]
    repairs = []
    for axis, plane in zip(mirror_axes, planes):
        for defect in find_defects([tuple(vertex) for vertex in moved],
                                   faces, axis, plane):
            moved[defect["vertex"]][axis] = defect["to"]
            repairs.append(defect)
    if strict and not repairs:
        raise SeamRefusal(
            "no vertex matched the documented seam predicate; see "
            "docs/design/st-maria-seam-defect.md")
    return [tuple(vertex) for vertex in moved], repairs
