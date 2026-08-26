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
        self.straw = material("wax")
        self.crock = material("bone")
        self.daylight = emissive("sr_window_daylight", (0.92, 0.95, 1.0))
        # Dim on purpose. make_material emits at strength 1.2, so a near-white
        # colour clips to a flat lightbox; this keeps a lit doorway reading as
        # lamplight spilling from a room rather than a glowing panel.
        self.lamplight = emissive("sr_lamp_glow", (0.46, 0.28, 0.13))
        # Warm, intense incandescence for the bakery oven fire and blacksmith forge.
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

    def back_wall(self, openings=(), mat=None):
        """Back wall built in segments around any number of openings.

        `openings` are (y0, y1, z0, z1) in wall coordinates. Segmenting rather
        than booleans keeps the mesh deterministic and low-poly, and keeps every
        face axis-aligned for the box-projected materials.
        """
        mat = mat or self.whitewash
        cx = self.back_x + self.wall_thick / 2.0
        top = self.wall_bottom + self.wall_height
        ordered = sorted(openings, key=lambda o: o[0])
        # Remembered so anything mounted on this wall -- a dado band, a
        # picture rail, a skirting -- can break around the same openings
        # instead of running straight over them.
        self.openings = list(ordered)

        edges = [-self.half_width]
        for y0, y1, _z0, _z1 in ordered:
            edges.extend((y0, y1))
        edges.append(self.half_width)

        for index in range(0, len(edges) - 1, 2):
            y0, y1 = edges[index], edges[index + 1]
            if y1 - y0 <= 1e-4:
                continue
            self.part(f"back_wall_pier_{index // 2}",
                      (self.wall_thick, y1 - y0, self.wall_height),
                      (cx, (y0 + y1) / 2.0, self.wall_bottom + self.wall_height / 2.0),
                      mat)

        for index, (y0, y1, z0, z1) in enumerate(ordered):
            if z0 - self.wall_bottom > 1e-4:
                self.part(f"back_wall_under_{index}",
                          (self.wall_thick, y1 - y0, z0 - self.wall_bottom),
                          (cx, (y0 + y1) / 2.0, (self.wall_bottom + z0) / 2.0), mat)
            if top - z1 > 1e-4:
                self.part(f"back_wall_over_{index}",
                          (self.wall_thick, y1 - y0, top - z1),
                          (cx, (y0 + y1) / 2.0, (z1 + top) / 2.0), mat)

    def side_walls(self, mat=None):
        mat = mat or self.whitewash
        centre = (self.front_x + self.back_x) / 2.0
        for index, y in enumerate((-self.half_width, self.half_width)):
            sign = -1.0 if y < 0 else 1.0
            self.part(f"side_wall_{index}",
                      (self.depth, self.wall_thick, self.wall_height),
                      (centre, y + sign * self.wall_thick / 2.0,
                       self.wall_bottom + self.wall_height / 2.0), mat)

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
