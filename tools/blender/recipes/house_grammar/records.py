"""The frozen output contract of the St. Maria house grammar.

Nothing in this package imports ``bpy``.  The grammar is a pure function from
a :class:`~house_grammar.recipe.BuildingRecipe` to an ordered list of
:class:`MeshRecord`, and Blender is demoted to an emitter that walks that list.
That split is what makes the grammar testable in the ordinary unit run instead
of behind a spawned Blender process.

**Local building frame.**  A record is authored in the building's own frame,
not in the scene:

    +X = depth INTO the building, away from the street
    +Y = along the street                    +Z = up
    origin = street-facing wall plane, ground level, at the building's lane
             centre

The emitter places the building by mapping this frame onto the exterior
authoring frame (``+X`` camera forward, ``-Y`` screen right, ``+Z`` up) through
``Exterior.y()``, so the determinant -1 basis of issue #935 is handled in
exactly one place and never leaks into the grammar.

**Roles.**  A building resolves to exactly one ``body`` record, exactly one
``roof`` record, and one record per opening assembly named ``door:<id>`` or
``window:<id>``.  Wings do not each get an object: multiple wings fuse into the
single body, and disconnected geometry islands inside one record are legal --
the authored houses use them.

**Materials are per face.**  ``face_materials`` carries a semantic id per face
(``"whitewash"``, ``"rough_limestone"``, ...), never a Blender material.  The
emitter resolves the semantic against the existing ``sr_*`` library, which
stays authoritative.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, replace

# Vertices are quantised to this grid before any welding or comparison. One
# micrometre is far below anything the camera can resolve and far above float
# noise from the rail arithmetic, so two rails that were computed by different
# routes still weld.
WELD = 1e-6
# The grid expressed as decimal places. Snapping through `round(value, 6)`
# rather than `round(value / WELD) * WELD` matters: the multiply-back reissues
# the float error it was meant to remove, so a rail computed as 1.0 - 0.6 lands
# on 0.39999999999999997 and every fingerprint and JSON dump carries the noise.
WELD_PLACES = 6

VALID_ROLES = ("body", "roof")
OPENING_ROLES = ("door", "window")


def quantise(value):
    """Snap one coordinate to the weld grid, mapping -0.0 onto 0.0."""
    return round(float(value), WELD_PLACES) + 0.0


def key(point):
    return tuple(quantise(axis) for axis in point)


@dataclass(frozen=True)
class ModifierSpec:
    """A modifier the emitter must install, rather than bake.

    Symmetry that is still intentional stays editable: a recipe that mirrors
    about the building's lane centre emits only the fundamental domain plus
    ``ModifierSpec("MIRROR", axes=("Y",))``.  A recipe that deliberately breaks
    symmetry -- a shop door off-centre under a symmetric roof -- bakes only the
    axis it broke, and says so in :attr:`BuildingRecipe.baked_axes`.
    """

    kind: str
    axes: tuple = ()
    settings: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in ("MIRROR",):
            raise ValueError(f"unsupported modifier kind {self.kind!r}")
        for axis in self.axes:
            if axis not in ("X", "Y", "Z"):
                raise ValueError(f"unsupported mirror axis {axis!r}")

    def as_json(self):
        return {"kind": self.kind, "axes": list(self.axes),
                "settings": dict(self.settings)}


@dataclass
class MeshRecord:
    """One semantic mesh: a body, a roof, or one opening assembly."""

    role: str
    name: str
    origin: tuple
    vertices: tuple = ()
    faces: tuple = ()
    face_materials: tuple = ()
    parent_role: str = None
    modifiers: tuple = ()
    metadata: dict = field(default_factory=dict)

    # -- introspection ----------------------------------------------------
    @property
    def semantic(self):
        """``body``, ``roof``, ``door`` or ``window`` -- the role without its id."""
        return self.role.split(":", 1)[0]

    @property
    def opening_id(self):
        return self.role.split(":", 1)[1] if ":" in self.role else None

    def bounds(self):
        """Local-frame ``(min, max)`` corners.  Empty records raise."""
        if not self.vertices:
            raise ValueError(f"record {self.name!r} has no vertices")
        axes = list(zip(*self.vertices))
        return (tuple(min(axis) for axis in axes),
                tuple(max(axis) for axis in axes))

    def world_vertices(self):
        ox, oy, oz = self.origin
        return tuple((x + ox, y + oy, z + oz) for x, y, z in self.vertices)

    def material_regions(self):
        """``{semantic: frozenset of face vertex-sets}`` -- the comparison unit.

        Conformance compares material *regions*, not face indices, because the
        authored houses were modelled by hand and their triangulation order
        carries no design intent.  A region is identified by the quantised
        world positions of the faces carrying that semantic, so a rebuild that
        splits one quad into two triangles still matches.
        """
        world = self.world_vertices()
        regions = {}
        for face, semantic in zip(self.faces, self.face_materials):
            entry = regions.setdefault(semantic, set())
            entry.add(frozenset(key(world[index]) for index in face))
        return {semantic: frozenset(faces) for semantic, faces in regions.items()}

    def fingerprint(self):
        """A stable digest of the record, for baseline storage and diffing."""
        digest = hashlib.sha256()
        digest.update(self.role.encode("utf-8"))
        digest.update(repr(key(self.origin)).encode("utf-8"))
        for vertex in self.vertices:
            digest.update(repr(key(vertex)).encode("utf-8"))
        for face, semantic in zip(self.faces, self.face_materials):
            digest.update(repr(tuple(face)).encode("utf-8"))
            digest.update(semantic.encode("utf-8"))
        for modifier in self.modifiers:
            digest.update(repr(modifier.as_json()).encode("utf-8"))
        return digest.hexdigest()

    def as_json(self):
        return {
            "role": self.role, "name": self.name,
            "origin": [quantise(axis) for axis in self.origin],
            "vertices": [[quantise(axis) for axis in vertex]
                         for vertex in self.vertices],
            "faces": [list(face) for face in self.faces],
            "faceMaterials": list(self.face_materials),
            "parentRole": self.parent_role,
            "modifiers": [modifier.as_json() for modifier in self.modifiers],
            "metadata": dict(self.metadata),
            "fingerprint": self.fingerprint(),
        }


def face_area(vertices, face):
    """Newell's area of one polygon.  Works for non-planar faces too."""
    normal = [0.0, 0.0, 0.0]
    count = len(face)
    for index in range(count):
        ax, ay, az = vertices[face[index]]
        bx, by, bz = vertices[face[(index + 1) % count]]
        normal[0] += (ay - by) * (az + bz)
        normal[1] += (az - bz) * (ax + bx)
        normal[2] += (ax - bx) * (ay + by)
    return 0.5 * math.sqrt(sum(component * component for component in normal))


def face_normal(vertices, face):
    normal = [0.0, 0.0, 0.0]
    count = len(face)
    for index in range(count):
        ax, ay, az = vertices[face[index]]
        bx, by, bz = vertices[face[(index + 1) % count]]
        normal[0] += (ay - by) * (az + bz)
        normal[1] += (az - bz) * (ax + bx)
        normal[2] += (ax - bx) * (ay + by)
    length = math.sqrt(sum(component * component for component in normal))
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return tuple(component / length for component in normal)


class GrammarError(ValueError):
    """Raised when a record violates the contract.  Never caught inside the
    grammar: a malformed record is a bug in a builder, not a recoverable
    condition."""


# The area below which a face is treated as degenerate. A square millimetre is
# two orders of magnitude smaller than the thinnest authored member (a 0.06 m
# grille bar) and well above weld-grid noise.
MIN_FACE_AREA = 1e-6


def validate(record):
    """Assert the contract on one record.  Returns the record for chaining."""
    if record.semantic not in VALID_ROLES + OPENING_ROLES:
        raise GrammarError(f"{record.name}: unknown role {record.role!r}")
    if record.semantic in OPENING_ROLES and not record.opening_id:
        raise GrammarError(f"{record.name}: role {record.role!r} needs an id")
    if record.semantic in VALID_ROLES and record.opening_id:
        raise GrammarError(f"{record.name}: role {record.role!r} takes no id")
    if len(record.faces) != len(record.face_materials):
        raise GrammarError(
            f"{record.name}: {len(record.faces)} faces but "
            f"{len(record.face_materials)} face materials")
    if not record.faces:
        raise GrammarError(f"{record.name}: no faces")
    count = len(record.vertices)
    for position, face in enumerate(record.faces):
        if len(face) < 3:
            raise GrammarError(f"{record.name}: face {position} has {len(face)} vertices")
        if len(set(face)) != len(face):
            raise GrammarError(f"{record.name}: face {position} repeats a vertex")
        for index in face:
            if not 0 <= index < count:
                raise GrammarError(
                    f"{record.name}: face {position} indexes vertex {index} "
                    f"of {count}")
        if face_area(record.vertices, face) < MIN_FACE_AREA:
            raise GrammarError(f"{record.name}: face {position} is degenerate")
    for semantic in record.face_materials:
        if not isinstance(semantic, str) or not semantic:
            raise GrammarError(f"{record.name}: empty material semantic")
    seen = {}
    for position, face in enumerate(record.faces):
        signature = frozenset(face)
        if signature in seen:
            raise GrammarError(
                f"{record.name}: faces {seen[signature]} and {position} share "
                "every vertex -- an internal face survived the fuse")
        seen[signature] = position
    used = {index for face in record.faces for index in face}
    if len(used) != count:
        orphans = sorted(set(range(count)) - used)
        raise GrammarError(f"{record.name}: vertices {orphans[:8]} are unused")
    return record


class MeshBuilder:
    """Accumulates welded geometry for one semantic mesh.

    The builder is what makes "one body mesh" true rather than aspirational.
    Adding two boxes that share a face does not leave that face inside the
    solid: :meth:`add_face` cancels a face against an existing face with the
    same vertex set, which is exactly the internal-face condition.  Callers
    therefore compose a wing out of overlapping courses without having to
    reason about what ends up buried.
    """

    def __init__(self, name):
        self.name = name
        self._vertices = []
        self._index = {}
        self._faces = []
        self._materials = []

    # -- vertices ---------------------------------------------------------
    def vertex(self, point):
        """Index of ``point``, welding onto an existing vertex when coincident."""
        signature = key(point)
        existing = self._index.get(signature)
        if existing is not None:
            return existing
        self._index[signature] = len(self._vertices)
        self._vertices.append(signature)
        return len(self._vertices) - 1

    # -- faces ------------------------------------------------------------
    def add_face(self, points, semantic):
        """Add one polygon.  A face that duplicates an existing one cancels it.

        Returns ``True`` when the face was added and ``False`` when it
        cancelled a coincident face, so a builder can count how much of its
        own geometry was interior.
        """
        indices = tuple(self.vertex(point) for point in points)
        if len(set(indices)) != len(indices):
            # Collapsed by the weld: a zero-width course, not an error here.
            return False
        signature = frozenset(indices)
        for position, face in enumerate(self._faces):
            if face is not None and frozenset(face) == signature:
                self._faces[position] = None
                self._materials[position] = None
                return False
        self._faces.append(indices)
        self._materials.append(semantic)
        return True

    def add_box(self, low, high, semantic, *, faces=None):
        """Six faces of an axis-aligned box, outward-facing.

        ``faces`` optionally restricts which sides are emitted, using the keys
        ``-x +x -y +y -z +z``; a course that is known to be buried can skip
        its buried side rather than relying on cancellation.
        """
        x0, y0, z0 = (quantise(axis) for axis in low)
        x1, y1, z1 = (quantise(axis) for axis in high)
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        if z1 < z0: z0, z1 = z1, z0
        if x1 - x0 < WELD or y1 - y0 < WELD or z1 - z0 < WELD:
            raise GrammarError(f"{self.name}: degenerate box {low} -> {high}")
        sides = {
            "-x": [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
            "+x": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            "-y": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            "+y": [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)],
            "-z": [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
            "+z": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        }
        wanted = sides if faces is None else {k: sides[k] for k in faces}
        added = 0
        for points in wanted.values():
            if isinstance(semantic, dict):
                raise GrammarError("per-side semantics take add_box_sided")
            added += 1 if self.add_face(points, semantic) else 0
        return added

    def add_box_sided(self, low, high, semantics, *, default=None):
        """A box whose sides carry different semantics.

        ``semantics`` maps ``-x +x -y +y -z +z`` onto semantic ids; sides
        absent from the mapping fall back to ``default`` and are skipped when
        there is none.  This is how a wall course carries whitewash on the
        street face and rough limestone on its return.
        """
        for side in ("-x", "+x", "-y", "+y", "-z", "+z"):
            semantic = semantics.get(side, default)
            if semantic is None:
                continue
            self.add_box(low, high, semantic, faces=(side,))

    # -- result -----------------------------------------------------------
    def record(self, role, *, origin=(0.0, 0.0, 0.0), parent_role=None,
               modifiers=(), metadata=None):
        """Compact the accumulated geometry into a validated record.

        Cancelled faces are dropped and the vertex list is rebuilt in first-use
        order, so the output is a function of the geometry rather than of the
        order in which interior faces happened to cancel.
        """
        remap = {}
        vertices = []
        faces = []
        materials = []
        for face, semantic in zip(self._faces, self._materials):
            if face is None:
                continue
            rebuilt = []
            for index in face:
                if index not in remap:
                    remap[index] = len(vertices)
                    vertices.append(self._vertices[index])
                rebuilt.append(remap[index])
            faces.append(tuple(rebuilt))
            materials.append(semantic)
        ox, oy, oz = (quantise(axis) for axis in origin)
        local = tuple((x - ox, y - oy, z - oz) for x, y, z in vertices)
        record = MeshRecord(
            role=role, name=self.name, origin=(ox, oy, oz),
            vertices=local, faces=tuple(faces),
            face_materials=tuple(materials), parent_role=parent_role,
            modifiers=tuple(modifiers), metadata=dict(metadata or {}),
        )
        return validate(record)

    def is_empty(self):
        return not any(face is not None for face in self._faces)


def recentre(record, origin):
    """Move a record's origin without moving its geometry in the world."""
    ox, oy, oz = (quantise(axis) for axis in origin)
    world = record.world_vertices()
    moved = tuple((x - ox, y - oy, z - oz) for x, y, z in world)
    return validate(replace(record, origin=(ox, oy, oz), vertices=moved))
