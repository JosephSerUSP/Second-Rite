"""The validated recipe schema, and the one entry point that builds from it.

A recipe describes a building in the vocabulary of its architecture -- wings,
courses, roof sections, openings, a palette -- and never in vertices.  If a
recipe needs a vertex table to say what it means, the grammar is missing an
operation and the operation is what should be added.

Everything here is plain data with eager validation.  A malformed recipe fails
at construction with a message naming the field, because a recipe that only
fails once it reaches Blender costs a round trip through a GUI to diagnose.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .records import GrammarError, quantise

# Material semantics already present in St. Maria.  The grammar may only name
# these: the library is authoritative, and a recipe inventing a semantic would
# emit faces the emitter cannot resolve.
SEMANTICS = (
    "whitewash", "azulejo", "terracotta", "roof_tile", "dark_wood",
    "rough_limestone", "old_limestone", "wrought_iron", "smoked_glass",
)

ROOF_PROFILES = ("gable", "hip", "half_hip", "lean_to", "cross_gable")
RIDGE_AXES = ("X", "Y")
COURSE_KINDS = ("plinth", "masonry", "storey", "band", "cornice", "eave",
                "gable_cap")
OPENING_KINDS = ("door", "window")


def _number(value, field_name, *, minimum=None, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise GrammarError(f"{field_name} must be a number, got {value!r}")
    if number != number or number in (float("inf"), float("-inf")):
        raise GrammarError(f"{field_name} must be finite, got {value!r}")
    if positive and number <= 0.0:
        raise GrammarError(f"{field_name} must be positive, got {number}")
    if minimum is not None and number < minimum:
        raise GrammarError(f"{field_name} must be >= {minimum}, got {number}")
    return quantise(number)


def _semantic(value, field_name):
    if value not in SEMANTICS:
        raise GrammarError(
            f"{field_name}: {value!r} is not a St. Maria material semantic "
            f"({', '.join(SEMANTICS)})")
    return value


@dataclass(frozen=True)
class Course:
    """One horizontal band of a wing, stacked from the ground up.

    A course is a *rail*, not a box: it declares where a horizontal boundary
    sits and how the wall steps at it.  ``inset`` moves the wall face in depth
    (negative projects it toward the street, which is how a cornice and a
    projected band are the same operation), and the grammar tessellates the
    façade between consecutive rails.
    """

    kind: str
    height: float
    semantic: str
    inset: float = 0.0
    # A course may carry a different semantic on the returns than on the
    # street face -- whitewash front, rough limestone corner.
    return_semantic: str = None

    def __post_init__(self):
        if self.kind not in COURSE_KINDS:
            raise GrammarError(f"course kind {self.kind!r} is not one of {COURSE_KINDS}")
        object.__setattr__(self, "height", _number(self.height, f"course {self.kind}.height", positive=True))
        object.__setattr__(self, "inset", _number(self.inset, f"course {self.kind}.inset"))
        _semantic(self.semantic, f"course {self.kind}.semantic")
        if self.return_semantic is not None:
            _semantic(self.return_semantic, f"course {self.kind}.return_semantic")


@dataclass(frozen=True)
class Wing:
    """One rectangular footprint with its own vertical course stack.

    Wings are combined into a single body: overlapping wings fuse, and the
    exposed perimeter loop is what gets walls.  An L-plan, a cross-wing and a
    stepped terrace front are all "two wings with different setbacks", which is
    the whole point of not modelling them as separate objects.
    """

    id: str
    lane_offset: float          # centre along +Y, from the building's lane centre
    width: float                # extent along Y
    depth: float                # extent along X, away from the street
    setback: float = 0.0        # +X pushes this wing back out of the terrace line
    courses: tuple = ()

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise GrammarError("wing id must be a non-empty string")
        object.__setattr__(self, "lane_offset", _number(self.lane_offset, f"wing {self.id}.lane_offset"))
        object.__setattr__(self, "width", _number(self.width, f"wing {self.id}.width", positive=True))
        object.__setattr__(self, "depth", _number(self.depth, f"wing {self.id}.depth", positive=True))
        object.__setattr__(self, "setback", _number(self.setback, f"wing {self.id}.setback"))
        if not self.courses:
            raise GrammarError(f"wing {self.id} has no courses")
        object.__setattr__(self, "courses", tuple(self.courses))

    @property
    def eave_z(self):
        """Top of the last non-gable course -- where the roof sits."""
        return quantise(sum(course.height for course in self.courses
                            if course.kind != "gable_cap"))

    @property
    def top_z(self):
        return quantise(sum(course.height for course in self.courses))

    def y_span(self):
        half = self.width / 2.0
        return (quantise(self.lane_offset - half), quantise(self.lane_offset + half))

    def x_span(self):
        return (quantise(self.setback), quantise(self.setback + self.depth))


@dataclass(frozen=True)
class RoofSection:
    """One roof over one wing, fused with its neighbours into a single mesh."""

    wing: str
    profile: str = "gable"
    ridge_axis: str = "Y"
    rise: float = 2.0
    overhang: float = 0.3
    thickness: float = 0.18
    ridge_offset: float = 0.0
    # half_hip only: the fraction of the rise at which the hipped end stops.
    hip_fraction: float = 0.5
    semantic: str = "roof_tile"
    # A stepped eave drops the eave line by this much on the +Y end, which is
    # how the authored terrace steps down the slope without breaking the ridge.
    eave_step: float = 0.0

    def __post_init__(self):
        if self.profile not in ROOF_PROFILES:
            raise GrammarError(f"roof profile {self.profile!r} is not one of {ROOF_PROFILES}")
        if self.ridge_axis not in RIDGE_AXES:
            raise GrammarError(f"ridge axis {self.ridge_axis!r} is not one of {RIDGE_AXES}")
        for name, positive in (("rise", True), ("overhang", False),
                               ("thickness", True), ("ridge_offset", False),
                               ("eave_step", False)):
            object.__setattr__(self, name, _number(getattr(self, name),
                                                   f"roof {self.wing}.{name}",
                                                   positive=positive))
        fraction = _number(self.hip_fraction, f"roof {self.wing}.hip_fraction")
        if not 0.0 < fraction < 1.0:
            raise GrammarError(f"roof {self.wing}.hip_fraction must be in (0, 1)")
        object.__setattr__(self, "hip_fraction", fraction)
        _semantic(self.semantic, f"roof {self.wing}.semantic")


@dataclass(frozen=True)
class Opening:
    """One door or window assembly, placed on a wing's street face.

    ``lane_offset`` is absolute in the building frame, not relative to the
    wing, because a runtime doorway anchor names a lane position and the
    picture of the door has to land on exactly that position.
    """

    id: str
    kind: str
    wing: str
    lane_offset: float
    width: float
    height: float
    sill_z: float = 0.0
    profile: str = "plain"
    # Layered members the assembly includes.  The authored openings are built
    # from these and nothing else.
    reveal: float = 0.16
    jamb: float = 0.16
    lintel: bool = True
    drip: bool = False
    sill: bool = True
    shutters: bool = False
    grille: bool = False
    pediment: bool = False
    panels: int = 0
    lit: bool = False

    def __post_init__(self):
        if self.kind not in OPENING_KINDS:
            raise GrammarError(f"opening {self.id}: kind {self.kind!r} is not one of {OPENING_KINDS}")
        if not self.id or ":" in self.id:
            raise GrammarError(f"opening id {self.id!r} must be non-empty and free of ':'")
        for name, positive in (("lane_offset", False), ("width", True),
                               ("height", True), ("sill_z", False),
                               ("reveal", True), ("jamb", True)):
            object.__setattr__(self, name, _number(getattr(self, name),
                                                   f"opening {self.id}.{name}",
                                                   positive=positive))
        if self.kind == "door" and self.sill_z != 0.0:
            raise GrammarError(f"opening {self.id}: a door sits on the threshold, sill_z must be 0")
        if int(self.panels) < 0:
            raise GrammarError(f"opening {self.id}: panels must not be negative")
        object.__setattr__(self, "panels", int(self.panels))

    @property
    def role(self):
        return f"{self.kind}:{self.id}"

    def y_span(self):
        half = self.width / 2.0
        return (quantise(self.lane_offset - half), quantise(self.lane_offset + half))


@dataclass(frozen=True)
class BuildingRecipe:
    """The complete description of one building."""

    id: str
    version: int
    wings: tuple
    roof: tuple
    openings: tuple = ()
    # Axes about which the building is symmetric and the emitter should install
    # an editable Mirror instead of the grammar duplicating geometry.
    mirror_axes: tuple = ()
    # Axes that WOULD be symmetric but which this recipe deliberately breaks,
    # and therefore bakes.  Declaring the break is what lets the symmetry test
    # tell an intentional asymmetry from a bug.
    baked_axes: tuple = ()
    palette: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            raise GrammarError("recipe id must be non-empty")
        if int(self.version) < 1:
            raise GrammarError(f"recipe {self.id}: version must be >= 1")
        object.__setattr__(self, "version", int(self.version))
        object.__setattr__(self, "wings", tuple(self.wings))
        object.__setattr__(self, "roof", tuple(self.roof))
        object.__setattr__(self, "openings", tuple(self.openings))
        object.__setattr__(self, "mirror_axes", tuple(self.mirror_axes))
        object.__setattr__(self, "baked_axes", tuple(self.baked_axes))
        if not self.wings:
            raise GrammarError(f"recipe {self.id}: at least one wing is required")
        ids = [wing.id for wing in self.wings]
        if len(set(ids)) != len(ids):
            raise GrammarError(f"recipe {self.id}: duplicate wing ids {ids}")
        known = set(ids)
        for section in self.roof:
            if section.wing not in known:
                raise GrammarError(
                    f"recipe {self.id}: roof section names unknown wing {section.wing!r}")
        roofed = [section.wing for section in self.roof]
        if len(set(roofed)) != len(roofed):
            raise GrammarError(f"recipe {self.id}: two roof sections over one wing")
        opening_ids = [opening.id for opening in self.openings]
        if len(set(opening_ids)) != len(opening_ids):
            raise GrammarError(f"recipe {self.id}: duplicate opening ids {opening_ids}")
        for opening in self.openings:
            if opening.wing not in known:
                raise GrammarError(
                    f"recipe {self.id}: opening {opening.id} names unknown wing "
                    f"{opening.wing!r}")
        for axis in self.mirror_axes + self.baked_axes:
            if axis not in ("X", "Y", "Z"):
                raise GrammarError(f"recipe {self.id}: unknown axis {axis!r}")
        overlap = set(self.mirror_axes) & set(self.baked_axes)
        if overlap:
            raise GrammarError(
                f"recipe {self.id}: axes {sorted(overlap)} are both mirrored and "
                "baked -- an axis is one or the other")

    def wing(self, wing_id):
        for wing in self.wings:
            if wing.id == wing_id:
                return wing
        raise GrammarError(f"recipe {self.id}: no wing {wing_id!r}")

    def roof_section(self, wing_id):
        for section in self.roof:
            if section.wing == wing_id:
                return section
        return None

    def as_json(self):
        return {"id": self.id, "version": self.version,
                "wings": [wing.__dict__ for wing in self.wings],
                "mirrorAxes": list(self.mirror_axes),
                "bakedAxes": list(self.baked_axes),
                "metadata": dict(self.metadata)}


def build(recipe):
    """The grammar: one recipe in, an ordered list of mesh records out.

    Ordering is fixed -- body, roof, then openings in recipe order -- because a
    stable order is what makes the baseline diff readable when the owner has
    hand-edited one assembly out of nine.
    """
    from . import body, openings as openings_module, roof

    records = [body.build_body(recipe)]
    if recipe.roof:
        records.append(roof.build_roof(recipe))
    records.extend(openings_module.build_openings(recipe))
    return records
