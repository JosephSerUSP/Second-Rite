"""Shared vocabulary for St. Maria interiors authored to the town camera.

St. Maria is a **colonial Portuguese** town. Walls default to limewash
(*caiacao*), floors and joinery to dark hardwood, and the furnishing grammar
lives in `furnishings.py`. See `docs/design/st-maria-interior-authoring.md`.

Every interior is the same handful of moves -- a floor with a thickness, a back
wall with openings punched through it, side walls, a ceiling, thresholds, and a
light rig that never uses a key. Keeping those here means a map file declares
only what makes that place itself, and a change to the vocabulary (the
threshold convention, the floor edge, the way a window is lit) reaches every
map at once instead of needing one edit per copy.

Authoring frame, in metres:

    +X = camera forward (depth)   -Y = screen right   +Z = up
    walkable floor at Z = 0, action plane at X = 0

Only the FLOOR LEVEL is fixed by the camera. Width, height and depth are free
per map, and a room may be far deeper than the player can walk.

The `.blend` each recipe writes is SOURCE AUTHORITY. `save_source_blend`
refuses to overwrite one that already exists, because ordinary work must never
discard hand-authoring -- the same rule `docs/asset-pipeline/BLENDER_CORE.md`
states for item documents.
"""

from __future__ import annotations

import contextlib
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import material_library  # noqa: E402
import second_rite_asset_core as asset_core  # noqa: E402
from first_stratum.common import box  # noqa: E402

CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"
ENVIRONMENT_DIR = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                   / "authoring" / "environments")

FLOOR_EDGE_NATIVE_Y = 136.0   # a few px above the 144 character floor limit
THRESHOLD_NATIVE_Y = 143.0    # an outward tab reaches almost to the limit


# The lowest native scanline a character may stand on before the engine would
# need Y camera scrolling. Characters normally stand at 128.
CHARACTER_FLOOR_LIMIT = 144.0


def camera_record():
    return json.loads(CAMERA.read_text(encoding="utf-8"))


def floor_edge_x(native_y, record=None):
    """World X where the floor plane (z=0) crosses a native scanline.

    Inverts the projection: a point at height 0 sits
    (baseHeight * eyeZ) / (2 * fovHalfY * depth) pixels below the horizon.
    """
    record = record or camera_record()
    k = record["baseViewportHeight"] / (2.0 * record["fovHalfY"])
    depth = k * record["eye"]["z"] / (float(native_y) - record["viewportCenterY"])
    return record["eye"]["x"] + depth, depth


def native_y_at(x, z, record=None):
    """Native scanline a world point projects to. The inverse of
    `floor_edge_x`, generalised off the floor plane.

    This is how you check a composition against the frame without rendering
    it: Y = 0 is the top of the screen, Y = 144 is the CHARACTER FLOOR LIMIT,
    and Y = 240 is the bottom. Anything below 144 is under the status menu.
    """
    record = record or camera_record()
    k = record["baseViewportHeight"] / (2.0 * record["fovHalfY"])
    depth = float(x) - record["eye"]["x"]
    if depth <= 1e-6:
        raise ValueError(f"x={x} is at or behind the camera")
    return record["viewportCenterY"] + k * (record["eye"]["z"] - float(z)) / depth


def native_x_at(x, y, record=None):
    """Native column a world point projects to, at the DEFAULT 256px width.

    Remember the handedness: -y is screen RIGHT, so a larger y is a smaller
    column.
    """
    record = record or camera_record()
    depth = float(x) - record["eye"]["x"]
    if depth <= 1e-6:
        raise ValueError(f"x={x} is at or behind the camera")
    half_px = record["baseViewportWidth"] / 2.0
    return half_px - (float(y) / base_half_width_at(depth, record)) * half_px


def half_width_at(depth, record=None):
    record = record or camera_record()
    return record["fovHalfX"] * depth * (record["targetWidth"]
                                         / record["baseViewportWidth"])


def base_half_width_at(depth, record=None):
    """Half-width in metres visible at the game's DEFAULT 256px width.

    `half_width_at` answers the same question for the wide 426px variant. A
    self-contained interior -- one that should not scroll -- is sized against
    this one, because a room wider than the default view promises the player a
    screen edge they can walk to.
    """
    record = record or camera_record()
    return record["fovHalfX"] * depth


def material(semantic_id):
    """Bind a semantic ID; the library supplies textures when they exist."""
    return material_library.build_material(asset_core, semantic_id)


def emissive(name, colour):
    return asset_core.make_material(name, color=colour, emission=colour)


class Interior:
    """One interior, built from the shared vocabulary."""

    def __init__(self, asset_id, *, half_width, depth, ceiling_z,
                 floor_thick=0.35, wall_thick=0.5, ceiling_thick=0.3,
                 floor_edge_native_y=FLOOR_EDGE_NATIVE_Y):
        asset_core.reset_scene()
        self.asset_id = asset_id
        self.record = camera_record()
        self.front_x, self.front_depth = floor_edge_x(floor_edge_native_y,
                                                      self.record)
        self.half_width = float(half_width)
        self.depth = float(depth)
        self.back_x = self.front_x + self.depth
        self.ceiling_z = float(ceiling_z)
        self.floor_thick = float(floor_thick)
        self.wall_thick = float(wall_thick)
        self.ceiling_thick = float(ceiling_thick)
        self.parts = []
        self.openings = []
        self.alcoves = []
        self.side_openings = {-1: [], 1: []}
        self.foreground_coverage = 0.0

        self.root = bpy.data.objects.new(asset_id.upper(), None)
        bpy.context.collection.objects.link(self.root)
        self.root.empty_display_type = "PLAIN_AXES"

        self.wood = material("dark_wood")
        # Walls default to limewash, not grey plaster: St. Maria is a colonial
        # Portuguese town and caiacao is its default surface.
        self.whitewash = material("whitewash")
        self.azulejo = material("azulejo")
        self.terracotta = material("terracotta")
        self.plaster = material("old_limestone")
        self.stone = material("rough_limestone")
        self.cloth = material("aged_cloth")
        self.iron = material("wrought_iron")
        self.bronze = material("oxidized_bronze")
        self.forge_scale = material("forge_scale")
        self.charcoal = material("charcoal")
        self.bread = material("bread_crust")
        self.straw = material("wax")
        self.crock = material("bone")
        self.daylight = emissive("sr_window_daylight", (0.92, 0.95, 1.0))
        # Dim on purpose. make_material emits at strength 1.2, so a near-white
        # colour clips to a flat lightbox; this keeps a lit doorway reading as
        # lamplight spilling from a room rather than a glowing panel.
        self.lamplight = emissive("sr_lamp_glow", (0.46, 0.28, 0.13))
        # A fire is the one source in this vocabulary that is BOTH a surface
        # and a light. The emissive bed makes the coals read hot; it casts
        # nothing, so a hearth still needs a `light` beside it.
        self.embers = emissive("sr_hearth_embers", (0.88, 0.26, 0.04))

    # -- geometry ---------------------------------------------------------
    def part(self, name, size, location, mat, **kw):
        obj = box(name, self.root, size, location, mat, asset_core, **kw)
        self.parts.append(obj)
        return obj

    @property
    def wall_height(self):
        return self.ceiling_z + self.floor_thick

    @property
    def wall_bottom(self):
        return -self.floor_thick

    def floor(self, mat=None):
        centre = (self.front_x + self.back_x) / 2.0
        return self.part("floor", (self.depth, self.half_width * 2,
                                   self.floor_thick),
                         (centre, 0.0, -self.floor_thick / 2.0),
                         mat or self.wood)

    def _pierced_run(self, name, a0, a1, plane, thick, openings, mat,
                     axis="y"):
        """One straight run of wall, segmented around the openings in it.

        Segmenting rather than booleans keeps the mesh deterministic and
        low-poly, and keeps every face axis-aligned for the box-projected
        materials. `axis` says which world axis the run travels along, so the
        same routine builds a back wall (along y) and a side wall (along x).
        """
        top = self.wall_bottom + self.wall_height
        inner = sorted((o for o in openings if o[0] >= a0 - 1e-4
                        and o[1] <= a1 + 1e-4), key=lambda o: o[0])

        def piece(tag, span_lo, span_hi, z_lo, z_hi):
            if span_hi - span_lo <= 1e-4 or z_hi - z_lo <= 1e-4:
                return
            along = span_hi - span_lo
            mid = (span_lo + span_hi) / 2.0
            if axis == "y":
                size = (thick, along, z_hi - z_lo)
                loc = (plane, mid, (z_lo + z_hi) / 2.0)
            else:
                size = (along, thick, z_hi - z_lo)
                loc = (mid, plane, (z_lo + z_hi) / 2.0)
            self.part(f"{name}_{tag}", size, loc, mat)

        edges = [a0]
        for o0, o1, _z0, _z1 in inner:
            edges.extend((o0, o1))
        edges.append(a1)
        for index in range(0, len(edges) - 1, 2):
            piece(f"pier_{index // 2}", edges[index], edges[index + 1],
                  self.wall_bottom, top)
        for index, (o0, o1, z0, z1) in enumerate(inner):
            piece(f"under_{index}", o0, o1, self.wall_bottom, z0)
            piece(f"over_{index}", o0, o1, z1, top)

    def back_wall(self, openings=(), alcoves=(), mat=None, arch_z=None):
        """Back wall built around any number of openings and alcoves.

        `openings` are (y0, y1, z0, z1) in wall coordinates.

        `alcoves` are (y0, y1, depth): over that span the wall steps BACK by
        `depth`, and the recess gets its own floor, ceiling, two returns and a
        HEADER across its mouth at `arch_z`. The header is what makes a recess
        read as a recess at this camera -- without one the wall simply moves
        back, which from a level lens 18m away is nearly invisible, and the
        alcove reads as a bay rather than a niche.
        An alcove is the cheapest way out of the one-box plan -- it gives a
        hearth, a shrine or a bed somewhere to be that is not simply "against
        the back wall", and it puts a real corner in the silhouette.

        An opening is built into whichever run it falls in, so an alcove may
        have its own window. An opening may not straddle an alcove edge.
        """
        mat = mat or self.whitewash
        ordered = sorted(openings, key=lambda o: o[0])
        # Remembered so anything mounted on this wall -- a dado band, a
        # picture rail, a skirting -- can break around the same openings
        # instead of running straight over them.
        self.openings = list(ordered)
        recesses = sorted(alcoves, key=lambda a: a[0])
        self.alcoves = list(recesses)

        cursor = -self.half_width
        for y0, y1, depth in recesses:
            if y0 < cursor - 1e-4:
                raise ValueError(f"alcoves overlap at y={y0}")
            if depth <= 0.0:
                raise ValueError("an alcove steps BACK: depth must be > 0")
            cursor = y1
        if cursor > self.half_width + 1e-4:
            raise ValueError("an alcove runs past the side wall")

        for o0, o1, _z0, _z1 in ordered:
            for y0, y1, _d in recesses:
                if o0 < y1 - 1e-4 and o1 > y0 + 1e-4 and not (
                        o0 >= y0 - 1e-4 and o1 <= y1 + 1e-4):
                    raise ValueError(
                        f"opening ({o0}, {o1}) straddles the alcove edge at "
                        f"({y0}, {y1}); openings belong to one run or the "
                        "other")

        runs, cursor = [], -self.half_width
        for y0, y1, depth in recesses:
            if y0 > cursor + 1e-4:
                runs.append((cursor, y0, self.back_x))
            runs.append((y0, y1, self.back_x + depth))
            cursor = y1
        if cursor < self.half_width - 1e-4:
            runs.append((cursor, self.half_width, self.back_x))

        for index, (y0, y1, plane) in enumerate(runs):
            self._pierced_run(f"back_wall_{index}", y0, y1,
                              plane + self.wall_thick / 2.0, self.wall_thick,
                              ordered, mat, axis="y")

        top = self.wall_bottom + self.wall_height
        header_z = (self.ceiling_z * 0.72) if arch_z is None else float(arch_z)
        for index, (y0, y1, depth) in enumerate(recesses):
            centre = self.back_x + depth / 2.0
            # The mouth's header, in the ORIGINAL wall plane. This is the edge
            # the eye reads the recess from.
            if top - header_z > 1e-4:
                self.part(f"alcove_{index}_header",
                          (self.wall_thick, y1 - y0, top - header_z),
                          (self.back_x + self.wall_thick / 2.0,
                           (y0 + y1) / 2.0, (header_z + top) / 2.0), mat)
                self.part(f"alcove_{index}_lintel",
                          (self.wall_thick + 0.12, y1 - y0 + 0.2, 0.14),
                          (self.back_x + self.wall_thick / 2.0,
                           (y0 + y1) / 2.0, header_z + 0.07), self.wood)
            self.part(f"alcove_{index}_floor", (depth, y1 - y0,
                                                self.floor_thick),
                      (centre, (y0 + y1) / 2.0, -self.floor_thick / 2.0),
                      self.wood)
            self.part(f"alcove_{index}_ceiling",
                      (depth, y1 - y0, self.ceiling_thick),
                      (centre, (y0 + y1) / 2.0,
                       self.ceiling_z + self.ceiling_thick / 2.0), mat)
            for side, y in ((0, y0), (1, y1)):
                sign = -1.0 if side == 0 else 1.0
                self.part(f"alcove_{index}_return_{side}",
                          (depth, self.wall_thick, self.wall_height),
                          (centre, y - sign * self.wall_thick / 2.0,
                           self.wall_bottom + self.wall_height / 2.0), mat)

    def side_walls(self, openings=None, mat=None):
        """The two side walls, optionally pierced.

        `openings` is {-1: [(x0, x1, z0, z1), ...], 1: [...]}, keyed by the
        SIGN of the wall's y. A side window is the single cheapest change to
        how a room reads: it rakes light ACROSS the space instead of from
        behind the player, so the same furniture throws entirely different
        shadows and the room stops looking like a shoebox lit from the back.
        """
        mat = mat or self.whitewash
        openings = openings or {}
        self.side_openings = {-1: list(openings.get(-1, ())),
                              1: list(openings.get(1, ()))}
        for index, y in enumerate((-self.half_width, self.half_width)):
            sign = -1 if y < 0 else 1
            self._pierced_run(f"side_wall_{index}", self.front_x, self.back_x,
                              y + sign * self.wall_thick / 2.0,
                              self.wall_thick, self.side_openings[sign], mat,
                              axis="x")

    def ceiling(self, *, beams=0, beam_span=1.5, mat=None):
        mat = mat or self.wood
        centre = (self.front_x + self.back_x) / 2.0
        self.part("ceiling", (self.depth, self.half_width * 2, self.ceiling_thick),
                  (centre, 0.0, self.ceiling_z + self.ceiling_thick / 2.0), mat)
        half = beams // 2
        for index in range(-half, half + 1):
            self.part(f"ceiling_beam_{index + half}",
                      (self.depth, 0.24, 0.28),
                      (centre, index * beam_span, self.ceiling_z - 0.14), mat)

    # -- openings ---------------------------------------------------------
    def window(self, y0, y1, z0, z1, *, sill=True):
        """Daylight seen THROUGH the opening.

        On a black backdrop an opening is a hole onto the void -- a black
        rectangle where the room's brightest thing should be -- so the opening
        carries an emissive plane behind it.
        """
        self.part("window_daylight",
                  (0.06, y1 - y0, z1 - z0),
                  (self.back_x + self.wall_thick - 0.02, (y0 + y1) / 2.0,
                   (z0 + z1) / 2.0), self.daylight)
        if sill:
            self.part("window_sill",
                      (self.wall_thick + 0.16, y1 - y0 + 0.26, 0.1),
                      (self.back_x + self.wall_thick / 2.0 - 0.06,
                       (y0 + y1) / 2.0, z0), self.wood)

    def side_window(self, side, x0, x1, z0, z1, *, sill=True):
        """Daylight seen through a SIDE wall opening.

        Same rule as `window`: on a black backdrop an opening is a hole onto
        the void, so it carries an emissive plane. Pair it with
        `side_window_light` or the room gets a bright rectangle that lights
        nothing.
        """
        sign = -1 if side < 0 else 1
        y = sign * (self.half_width + self.wall_thick - 0.02)
        self.part(f"side_window_daylight_{0 if sign < 0 else 1}",
                  (x1 - x0, 0.06, z1 - z0),
                  ((x0 + x1) / 2.0, y, (z0 + z1) / 2.0), self.daylight)
        if sill:
            self.part(f"side_window_sill_{0 if sign < 0 else 1}",
                      (x1 - x0 + 0.26, self.wall_thick + 0.16, 0.1),
                      ((x0 + x1) / 2.0,
                       sign * (self.half_width + self.wall_thick / 2.0 - 0.06),
                       z0), self.wood)

    def side_window_light(self, side, x, z, *, energy=260.0):
        """Daylight raking in from a side wall, aimed ACROSS the room."""
        sign = -1 if side < 0 else 1
        return self.light(
            f"light_side_window_{0 if sign < 0 else 1}", "AREA",
            (x, sign * (self.half_width - 0.35), z),
            (-0.25, -sign * 0.85, -0.46), energy, (1.0, 0.96, 0.86),
            size=1.5, size_y=1.25)

    def platform(self, name, x0, x1, y0, y1, rise, *, mat=None, nosing=True):
        """A change of floor level: a raised dais, or a sunken pit.

        The floor LEVEL is the one fixed dimension in this vocabulary, so this
        is the axis that has to be spent carefully -- but a room where the
        player stands at two heights stops reading as one flat box.

        A raised platform is free: it moves a character UP the screen, away
        from the limit. A SUNKEN floor is not, so it is measured here rather
        than trusted -- a pit whose surface would push a character's feet past
        the character floor limit is refused, because that is the point at
        which the engine would need Y camera scrolling.
        """
        mat = mat or self.wood
        rise = float(rise)
        if abs(rise) < 1e-4:
            raise ValueError("a platform with no rise is just floor")
        if rise < 0.0:
            # Nearest edge is the worst case: it projects lowest.
            feet = native_y_at(min(x0, x1), rise, self.record)
            if feet > CHARACTER_FLOOR_LIMIT:
                raise SystemExit(
                    f"platform {name!r} sinks the floor to z={rise:+.3f}, "
                    f"which puts a character's feet at native Y={feet:.1f} -- "
                    f"past the character floor limit of "
                    f"{CHARACTER_FLOOR_LIMIT}. Raise it, or move it deeper "
                    "into the room where the projection is kinder."
                )
        thick = self.floor_thick
        self.part(f"{name}_deck", (x1 - x0, y1 - y0, thick),
                  ((x0 + x1) / 2.0, (y0 + y1) / 2.0, rise - thick / 2.0), mat)
        if rise > 0.0:
            # The riser faces the camera, so it is the edge that reads.
            self.part(f"{name}_riser", (thick, y1 - y0, rise),
                      (x0 - thick / 2.0, (y0 + y1) / 2.0, rise / 2.0), mat)
            if nosing:
                self.part(f"{name}_nosing", (0.12, y1 - y0, 0.05),
                          (x0 - thick, (y0 + y1) / 2.0, rise - 0.025), mat)
        return rise

    def partition(self, name, y, x0, x1, *, height=None, thick=None,
                  mat=None):
        """A stub wall running away from the camera, dividing the plan.

        Stops short of the ceiling by default so the room still reads as one
        space rather than two rooms in one shot -- which the vocabulary
        forbids.
        """
        mat = mat or self.whitewash
        thick = self.wall_thick if thick is None else float(thick)
        # Waist-to-chest, not shoulder. A tall stub next to the actor reads as
        # a blank pillar competing with them; a low one reads as furniture and
        # still breaks the floor plane.
        height = self.ceiling_z * 0.42 if height is None else float(height)
        self.part(f"{name}_wall", (x1 - x0, thick, height + self.floor_thick),
                  ((x0 + x1) / 2.0, y,
                   self.wall_bottom + (height + self.floor_thick) / 2.0), mat)
        self.part(f"{name}_cap", (x1 - x0, thick + 0.1, 0.1),
                  ((x0 + x1) / 2.0, y, height + 0.05), self.wood)
        # End posts. Without them the stub is a featureless slab, and a flat
        # unlit rectangle at this size reads as a hole rather than a wall.
        for side, x in ((0, x0), (1, x1)):
            sign = -1.0 if side == 0 else 1.0
            self.part(f"{name}_post_{side}", (0.16, thick + 0.1,
                                              height + self.floor_thick + 0.1),
                      (x - sign * 0.08, y,
                       self.wall_bottom + (height + self.floor_thick + 0.1) / 2.0),
                      self.wood)
        return height

    def foreground(self, name, ahead, *, span, z0, z1, mat=None,
                   thick=0.35, max_frame_fraction=0.25):
        """Geometry BETWEEN the camera and the room: a near-field occluder.

        `ahead` is metres in front of the room's front edge. `span` is
        (y_lo, y_hi) as a FRACTION of the visible half-width at that plane,
        so -1.0 and +1.0 are the frame edges and the numbers mean the same
        thing whatever `ahead` you choose.

        Nothing in the room is between the player and the action plane, which
        is why every interior so far has read as a flat picture: depth needs
        something to be in FRONT. An occluder gives the camera a foreground
        layer, and because the room's lights are all behind it, it reads as a
        dark silhouette -- which is the effect, not a fault.

        It has to stay PARTIAL. An occluder that covers the picture is a
        proscenium, which this vocabulary deliberately does not have -- it has
        a black backdrop. The guard measures what the member actually COVERS
        of the free 256x144 composition area, not how wide it is, and the
        budget is CUMULATIVE across every occluder in the room: a post at 6%
        and a beam at 12% are each harmless alone and close the frame down
        between them.

        The guard is a floor, not a recipe. Two things it cannot check, both
        learned by rendering the alternatives rather than reasoning about them:

        - **Overlap the room; do not line the frame.** A member flush against
          the frame edge -- a full-width beam at the top, a post hard against
          the side -- reads as letterboxing, because the ceiling and the side
          walls already draw those edges. An occluder earns its place by
          overlapping the ROOM, so something is demonstrably in front of
          something else.
        - **Give it something to catch.** Every light here is inside the room
          and aimed away, so an unlit occluder renders as a flat near-black
          shape, which at this size reads as damage rather than depth. Hang a
          lantern on the post, or put it where a window or a doorway spills
          onto it. That is also the in-vocabulary answer: the near layer gets
          lit by something the place contains, like everything else.
        """
        mat = mat or self.wood
        x = self.front_x - float(ahead)
        depth = x - self.record["eye"]["x"]
        if depth <= 1e-6:
            raise ValueError(f"{name!r} is at or behind the camera")
        half = base_half_width_at(depth, self.record)

        lo, hi = sorted(float(v) for v in span)
        y_lo, y_hi = lo * half, hi * half

        width = self.record["baseViewportWidth"]
        cols = sorted((native_x_at(x, y_lo, self.record),
                       native_x_at(x, y_hi, self.record)))
        rows = sorted((native_y_at(x, z0, self.record),
                       native_y_at(x, z1, self.record)))
        covered_w = max(0.0, min(cols[1], width) - max(cols[0], 0.0))
        covered_h = max(0.0, min(rows[1], CHARACTER_FLOOR_LIMIT)
                        - max(rows[0], 0.0))
        fraction = (covered_w * covered_h) / (width * CHARACTER_FLOOR_LIMIT)
        # The budget is CUMULATIVE. Guarding each member on its own lets two
        # legal members build an illegal proscenium between them, which is
        # exactly what the first draft of this grammar did: a post and a beam,
        # each comfortably under the limit, together closed the frame down.
        running = self.foreground_coverage + fraction
        if running > max_frame_fraction:
            already = (f" (this one is {fraction:.0%}; {self.foreground_coverage:.0%} "
                       "is already spent)" if self.foreground_coverage else "")
            raise SystemExit(
                f"foreground {name!r} takes the near layer to {running:.0%} of "
                f"the free {width:.0f}x{CHARACTER_FLOOR_LIMIT:.0f} composition "
                f"area{already}. An occluder that covers the picture is a "
                "proscenium, and this vocabulary does not have one. Narrow it, "
                "move it higher, or push it back toward the room."
            )
        self.foreground_coverage = running

        self.part(name, (thick, y_hi - y_lo, z1 - z0),
                  (x, (y_lo + y_hi) / 2.0, (z0 + z1) / 2.0), mat)
        return x

    def doorway(self, name, y0, y1, z1, *, recess=0.45, lit=None,
                open_back=False):
        """A door in the back wall, with the floor extruded INTO it.

        A threshold is an extrusion of the floor along the axis of travel: it
        says "this direction is passable" because it protrudes the way you
        would go. A corridor's doors lead away from the camera, so their
        thresholds run inward -- the mirror of a room's exit, which runs out
        toward the viewer.
        """
        cy = (y0 + y1) / 2.0
        # A room door is closed at the back of its recess. An opening the
        # player can see THROUGH -- a stair head, an arch onto a yard -- must
        # omit that panel, or whatever lies beyond is hidden behind it.
        if not open_back:
            self.part(f"{name}_reveal_back",
                      (0.12, y1 - y0, z1),
                      (self.back_x + self.wall_thick + 0.06, cy, z1 / 2.0),
                      self.wood if lit is None else self.lamplight)
        self.part(f"{name}_threshold",
                  (recess + self.wall_thick, y1 - y0 - 0.12, self.floor_thick),
                  (self.back_x + (recess + self.wall_thick) / 2.0, cy,
                   -self.floor_thick / 2.0), self.wood)
        self.part(f"{name}_lintel",
                  (self.wall_thick + 0.1, y1 - y0 + 0.22, 0.14),
                  (self.back_x + self.wall_thick / 2.0, cy, z1 + 0.07), self.wood)
        return cy

    def exit_threshold(self, y_centre, *, width=1.5,
                       native_y=THRESHOLD_NATIVE_Y):
        """The way OUT: floor extruded outward, toward the camera.

        Not raised. A raised square says "there is a thing here"; a tongue of
        floor projecting toward the viewer says "this direction is passable".
        This is why the floor stops short of the character floor limit -- the
        tab needs somewhere to project into.
        """
        tab_x, _ = floor_edge_x(native_y, self.record)
        tab_depth = self.front_x - tab_x
        self.part("exit_threshold", (tab_depth, width, self.floor_thick),
                  ((self.front_x + tab_x) / 2.0, y_centre,
                   -self.floor_thick / 2.0), self.wood)
        return (self.front_x + tab_x) / 2.0, y_centre

    # -- light ------------------------------------------------------------
    def light(self, name, kind, location, direction, energy, colour, **kw):
        """A canonical light source, authored as part of the place.

        No sun and no key anywhere in this vocabulary: a hard raking light is
        what makes an interior read as a diorama. Baseline visibility is the
        world light the stager supplies; every hard shadow here comes from
        something the place contains.
        """
        from mathutils import Vector

        data = bpy.data.lights.new(name, type=kind)
        data.energy = float(energy)
        data.color = tuple(colour)
        if kind == "AREA":
            data.shape = "RECTANGLE"
            data.size = kw.get("size", 1.0)
            data.size_y = kw.get("size_y", kw.get("size", 1.0))
        elif kind == "SPOT":
            data.spot_size = math.radians(kw.get("spot_degrees", 70.0))
            data.spot_blend = kw.get("spot_blend", 0.45)
        elif kind == "POINT":
            data.shadow_soft_size = kw.get("radius", 0.12)
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = Vector(location)
        obj.rotation_euler = Vector(direction).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        obj.parent = self.root
        obj.matrix_parent_inverse = self.root.matrix_world.inverted()
        obj["sr_canonical_light"] = True
        return obj

    def window_light(self, y, z, *, energy=260.0):
        return self.light("light_window", "AREA",
                          (self.back_x - 0.35, y, z), (-0.85, -0.18, -0.5),
                          energy, (1.0, 0.96, 0.86), size=1.5, size_y=1.25)

    def doorway_light(self, x, y, *, energy=26.0, colour=(0.80, 0.85, 1.0)):
        """Light falling on a threshold from the space beyond it."""
        return self.light("light_doorway_bounce", "AREA", (x, y, 1.5),
                          (0.55, 0.0, -0.85), energy, colour,
                          size=1.6, size_y=2.0)

    # -- pieces -----------------------------------------------------------
    @contextlib.contextmanager
    def piece(self, name):
        """Build one furnishing, and leave ONE object behind.

        Every mesh created inside the block is joined into a single object
        named `name`. The `.blend` is the hand-editable source document, so a
        chest has to arrive in the outliner as a chest -- not as five loose
        boxes the maintainer must re-identify and box-select before they can
        move it. Without this a furnished shop lands as ~100 sparse objects.

        A light cannot be joined into a mesh, so anything built with
        `Interior.light` inside the block stays a sibling of the joined piece.
        """
        start = len(self.parts)
        yield
        made = self.parts[start:]
        # Anything that is NOT joined has to be identified BEFORE the join:
        # join frees the merged-away objects, and touching one afterwards
        # raises "StructRNA of type Object has been removed".
        survivors = [obj for obj in made if obj.type != "MESH"]
        joined = join_parts(name, made, self.root)
        if joined is not None:
            self.parts[start:] = [joined] + survivors

    # -- finish -----------------------------------------------------------
    def finish(self, *, role="preview_only", authoring_space="preview",
               placement_frame="preview_frame"):
        recalculate_normals(self.parts)
        for obj in self.parts:
            obj.name = obj.name.lower()
        asset_core.tag_asset_target(
            self.root,
            asset_id=self.asset_id,
            representation="full_model",
            role=role,
            authoring_space=authoring_space,
            placement_frame=placement_frame,
            states=["default"],
            variants=[],
            extra={"sr_preview_only": True,
                   "sr_authoring_units": "metre",
                   "sr_town_camera": "tools/blender/fixtures/"
                                     "town_sideview_camera.json"},
        )
        asset_core.validate_asset_metadata(self.root)
        return self.root

    def bounds(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        coords = [(o.matrix_world @ v.co)
                  for o in self.parts if o.type == "MESH"
                  for v in o.evaluated_get(depsgraph).to_mesh().vertices]
        lo = [min(c[axis] for c in coords) for axis in range(3)]
        hi = [max(c[axis] for c in coords) for axis in range(3)]
        return lo, hi


def join_parts(name, objects, root):
    """Join meshes into one object named `name`, parented to `root`.

    `bpy.ops.object.join` keeps only the ACTIVE object's modifiers and drops
    everyone else's, so refuse rather than silently lose one. Today no recipe
    passes `bevel=`, so `common.box` adds no modifier at all and the join is
    lossless -- this guard is here so that stops being true loudly.
    """
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if not meshes:
        return None
    if len(meshes) == 1:
        meshes[0].name = name
        meshes[0].data.name = name
        return meshes[0]

    modified = [obj.name for obj in meshes[1:] if obj.modifiers]
    if modified:
        raise SystemExit(
            f"cannot join piece {name!r}: {modified} carry modifiers that "
            "bpy.ops.object.join would discard. Apply them, or build the "
            "piece outside Interior.piece()."
        )

    target = meshes[0]
    with bpy.context.temp_override(active_object=target, object=target,
                                   selected_objects=meshes,
                                   selected_editable_objects=meshes):
        bpy.ops.object.join()
    target.name = name
    target.data.name = name
    target.parent = root
    return target


def recalculate_normals(objects):
    """first_stratum.common.box emits INWARD normals (its bottom face reads
    +Z, its top face -Z). Outward winding is load-bearing for baking and for
    downstream surface detection. The shared helper is deliberately left
    alone: the Phase 4 item checks assert structural equivalence across the
    shipped OBJ corpus. See issue #936."""
    import bmesh
    for obj in objects:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def save_source_blend(blend: Path, *, force: bool):
    blend = Path(blend).resolve()
    if blend.exists() and not force:
        raise SystemExit(
            f"{blend} already exists and is the SOURCE AUTHORITY for this "
            "environment. This script only scaffolds a new one; it must never "
            "regenerate a document that has been hand-edited. Edit the .blend "
            "directly, or pass --force to discard it deliberately."
        )
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    return blend


def report(interior, blend, extra=None):
    lo, hi = interior.bounds()
    payload = {
        "assetId": interior.asset_id,
        "parts": len(interior.parts),
        "lights": sorted(o.name for o in bpy.data.objects if o.type == "LIGHT"),
        "blend": str(blend),
        "min": [round(v, 4) for v in lo],
        "max": [round(v, 4) for v in hi],
        "extent": [round(hi[i] - lo[i], 4) for i in range(3)],
    }
    payload.update(extra or {})
    print("RECIPE RESULT " + json.dumps(payload))
