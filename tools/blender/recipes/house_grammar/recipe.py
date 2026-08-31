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
ELEVATIONS = ("front", "back", "left", "right")
COURSE_TRANSITIONS = ("splay", "step")


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


def _validate_outline(recipe_id, raw):
    points = []
    for index, point in enumerate(raw):
        if not isinstance(point, (tuple, list)) or len(point) != 2:
            raise GrammarError(
                f"recipe {recipe_id}: outline point {index} must be an XY pair")
        points.append(tuple(_number(
            value, f"recipe {recipe_id}.outline[{index}]") for value in point))
    if not points:
        return ()
    if len(points) < 3:
        raise GrammarError(
            f"recipe {recipe_id}: outline must contain at least three XY points")
    if len(set(points)) != len(points):
        raise GrammarError(f"recipe {recipe_id}: outline repeats a point")
    area = sum(points[index][0] * points[(index + 1) % len(points)][1]
               - points[(index + 1) % len(points)][0] * points[index][1]
               for index in range(len(points)))
    if area <= 0.0:
        raise GrammarError(
            f"recipe {recipe_id}: outline must be a non-zero CCW boundary")

    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def on_segment(a, b, point):
        return (abs(orient(a, b, point)) <= 1e-9
                and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
                and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]))

    def intersects(a, b, c, d):
        values = (orient(a, b, c), orient(a, b, d),
                  orient(c, d, a), orient(c, d, b))
        if values[0] * values[1] < 0.0 and values[2] * values[3] < 0.0:
            return True
        return ((abs(values[0]) <= 1e-9 and on_segment(a, b, c))
                or (abs(values[1]) <= 1e-9 and on_segment(a, b, d))
                or (abs(values[2]) <= 1e-9 and on_segment(c, d, a))
                or (abs(values[3]) <= 1e-9 and on_segment(c, d, b)))

    count = len(points)
    for first in range(count):
        a, b = points[first], points[(first + 1) % count]
        for second in range(first + 1, count):
            if second in (first, (first + 1) % count) or \
                    (second + 1) % count == first:
                continue
            c, d = points[second], points[(second + 1) % count]
            if intersects(a, b, c, d):
                raise GrammarError(
                    f"recipe {recipe_id}: outline edges {first} and {second} cross")
    return tuple(points)


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
    transition: str = "splay"

    def __post_init__(self):
        if self.kind not in COURSE_KINDS:
            raise GrammarError(f"course kind {self.kind!r} is not one of {COURSE_KINDS}")
        object.__setattr__(self, "height", _number(self.height, f"course {self.kind}.height", positive=True))
        object.__setattr__(self, "inset", _number(self.inset, f"course {self.kind}.inset"))
        _semantic(self.semantic, f"course {self.kind}.semantic")
        if self.return_semantic is not None:
            _semantic(self.return_semantic, f"course {self.kind}.return_semantic")
        if self.transition not in COURSE_TRANSITIONS:
            raise GrammarError(
                f"course {self.kind}.transition {self.transition!r} is not one of "
                f"{COURSE_TRANSITIONS}")


@dataclass(frozen=True)
class PierSpec:
    """A proud masonry pier substituted for each convex plan corner."""

    width: float = 0.2
    project: float = 0.1
    splay: float = 0.1
    through: str = None

    def __post_init__(self):
        for name in ("width", "project", "splay"):
            object.__setattr__(self, name, _number(
                getattr(self, name), f"pier.{name}", positive=True))
        if self.through is not None and self.through not in COURSE_KINDS:
            raise GrammarError(
                f"pier.through {self.through!r} is not one of {COURSE_KINDS}")


@dataclass(frozen=True)
class CanopySpec:
    """A small lean-to roof carried by an opening assembly."""

    depth: float = 0.65
    rise: float = 0.18
    thickness: float = 0.08
    margin: float = 0.28
    semantic: str = "roof_tile"

    def __post_init__(self):
        for name in ("depth", "rise", "thickness", "margin"):
            object.__setattr__(self, name, _number(
                getattr(self, name), f"canopy.{name}", positive=True))
        _semantic(self.semantic, "canopy.semantic")


@dataclass(frozen=True)
class StepSpec:
    """A solid stepped approach in front of a door."""

    count: int = 2
    rise: float = 0.16
    run: float = 0.30
    margin: float = 0.24
    semantic: str = "rough_limestone"

    def __post_init__(self):
        if isinstance(self.count, bool) or int(self.count) != self.count or int(self.count) < 1:
            raise GrammarError(f"steps.count must be a positive integer, got {self.count!r}")
        object.__setattr__(self, "count", int(self.count))
        for name in ("rise", "run", "margin"):
            object.__setattr__(self, name, _number(
                getattr(self, name), f"steps.{name}", positive=True))
        _semantic(self.semantic, "steps.semantic")


@dataclass(frozen=True)
class BalconySpec:
    """A projecting stone balcony with a wrought-iron guard and brackets."""

    width: float = 1.8
    depth: float = 0.75
    slab: float = 0.14
    rail_height: float = 0.9
    rail_spacing: float = 0.18
    brackets: int = 2

    def __post_init__(self):
        for name in ("width", "depth", "slab", "rail_height", "rail_spacing"):
            object.__setattr__(self, name, _number(
                getattr(self, name), f"balcony.{name}", positive=True))
        if isinstance(self.brackets, bool) or int(self.brackets) != self.brackets \
                or int(self.brackets) < 0:
            raise GrammarError(
                f"balcony.brackets must be a non-negative integer, got {self.brackets!r}")
        object.__setattr__(self, "brackets", int(self.brackets))


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
    pier: PierSpec = None

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
        if self.pier is not None and not isinstance(self.pier, PierSpec):
            raise GrammarError(f"wing {self.id}.pier must be a PierSpec")

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
    canopy: CanopySpec = None
    steps: StepSpec = None
    elevation: str = "front"
    balcony: BalconySpec = None

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
        if self.canopy is not None and not isinstance(self.canopy, CanopySpec):
            raise GrammarError(f"opening {self.id}.canopy must be a CanopySpec")
        if self.steps is not None and not isinstance(self.steps, StepSpec):
            raise GrammarError(f"opening {self.id}.steps must be a StepSpec")
        if self.steps is not None and self.kind != "door":
            raise GrammarError(f"opening {self.id}: steps belong to a door, not a window")
        if self.elevation not in ELEVATIONS:
            raise GrammarError(
                f"opening {self.id}: elevation {self.elevation!r} is not one of {ELEVATIONS}")
        if self.balcony is not None and not isinstance(self.balcony, BalconySpec):
            raise GrammarError(f"opening {self.id}.balcony must be a BalconySpec")
        if self.balcony is not None and self.kind != "window":
            raise GrammarError(f"opening {self.id}: a balcony belongs to a window")
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
    # One coherent body boundary. Wings remain roof/opening zones; when this
    # is present they no longer compose the body from overlapping rectangles.
    outline: tuple = ()

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
        object.__setattr__(self, "outline", _validate_outline(self.id, self.outline))
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
        """The whole recipe as plain JSON-serialisable data.

        Every field is spelled out rather than taken from ``__dict__``: the
        nested dataclasses are not serialisable, and the emitter writes this
        onto the root as ``th_house_params`` -- provenance that raised on every
        real recipe is provenance that is never there when the diff needs it.
        """
        return {
            "id": self.id, "version": self.version,
            "wings": [
                {"id": wing.id, "laneOffset": wing.lane_offset,
                 "width": wing.width, "depth": wing.depth,
                 "setback": wing.setback,
                 "pier": ({"width": wing.pier.width,
                           "project": wing.pier.project,
                           "splay": wing.pier.splay,
                           "through": wing.pier.through}
                          if wing.pier is not None else None),
                 "courses": [{"kind": course.kind, "height": course.height,
                              "semantic": course.semantic,
                              "inset": course.inset,
                              "returnSemantic": course.return_semantic,
                              "transition": course.transition}
                             for course in wing.courses]}
                for wing in self.wings],
            "roof": [
                {"wing": section.wing, "profile": section.profile,
                 "ridgeAxis": section.ridge_axis, "rise": section.rise,
                 "overhang": section.overhang, "thickness": section.thickness,
                 "ridgeOffset": section.ridge_offset,
                 "hipFraction": section.hip_fraction,
                 "semantic": section.semantic, "eaveStep": section.eave_step}
                for section in self.roof],
            "openings": [
                {"id": opening.id, "kind": opening.kind, "wing": opening.wing,
                 "laneOffset": opening.lane_offset, "width": opening.width,
                 "height": opening.height, "sillZ": opening.sill_z,
                 "profile": opening.profile, "reveal": opening.reveal,
                 "jamb": opening.jamb, "lintel": bool(opening.lintel),
                 "drip": bool(opening.drip), "sill": bool(opening.sill),
                 "shutters": bool(opening.shutters),
                 "grille": bool(opening.grille),
                 "pediment": bool(opening.pediment),
                 "panels": opening.panels, "lit": bool(opening.lit),
                 "elevation": opening.elevation,
                 "canopy": ({"depth": opening.canopy.depth,
                             "rise": opening.canopy.rise,
                             "thickness": opening.canopy.thickness,
                             "margin": opening.canopy.margin,
                             "semantic": opening.canopy.semantic}
                            if opening.canopy is not None else None),
                 "steps": ({"count": opening.steps.count,
                            "rise": opening.steps.rise,
                            "run": opening.steps.run,
                            "margin": opening.steps.margin,
                            "semantic": opening.steps.semantic}
                           if opening.steps is not None else None),
                 "balcony": ({"width": opening.balcony.width,
                               "depth": opening.balcony.depth,
                               "slab": opening.balcony.slab,
                               "railHeight": opening.balcony.rail_height,
                               "railSpacing": opening.balcony.rail_spacing,
                               "brackets": opening.balcony.brackets}
                              if opening.balcony is not None else None)}
                for opening in self.openings],
            "outline": [list(point) for point in self.outline],
            "mirrorAxes": list(self.mirror_axes),
            "bakedAxes": list(self.baked_axes),
            "palette": dict(self.palette),
            "metadata": dict(self.metadata),
        }


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
