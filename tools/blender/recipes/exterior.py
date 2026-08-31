"""Shared vocabulary for St. Maria EXTERIORS authored to the town camera.

An exterior is not an interior with the ceiling taken off. Three things change,
and each is a measured consequence of the same calibrated camera rather than a
taste decision:

1. **The ground runs off the bottom of the frame.** An interior floor stops at
   the character floor limit and hands the last rows to a foreground floor,
   because a room is a cutaway seen from outside. A street is not: the player
   is standing IN it, so the ground plane continues toward the lens until it
   leaves the frame. It crosses native scanline 240 at X = -12.01, so that is
   where the slab starts.
2. **The bottom of the frame is under the status menu, and the menu is
   TRANSLUCENT.** Rows 144-240 are seen through it. Ground alone there reads as
   an empty apron, so an exterior puts near-camera architecture and planting in
   front of the action plane: the FOREGROUND BAND. Per the house definition,
   foreground is what the player passes BEHIND -- so the band runs along the
   lane through the columns the player actually walks, not just at the ends,
   where it would only be framing.
3. **The light comes from the sky.** Interiors take every hard shadow from a
   source the room contains, because a raking key makes a room read as a
   diorama. Outdoors the sky IS the source: a large, soft, cool dome fill plus
   one weak sun for direction. Still no harsh key -- the albedo doctrine holds,
   and textures carry their own ambient occlusion.

Authoring frame, in metres -- identical to `interior.py`:

    +X = camera forward (depth)   -Y = screen right   +Z = up
    walkable ground at Z = 0, action plane at X = 0

**The camera is the same camera.** A modelled exterior reuses
`fixtures/town_sideview_camera.json` unchanged, because character pixel scale is
fixed across the whole game: the solved distance 18.6667 renders a 1.75 m walker
at exactly 48 native px with its feet on scanline 128, indoors and out. The 2D
plate presentation of the same street uses a different, larger scale
(`playerProjection.pixelsPerRuntimeY` = 34.6 against this camera's 27.4286);
that number belongs to the plate, and a modelled screen must not inherit it.

Lane coordinates: the runtime lane runs 0..span west to east, and the engine's
screen-right is +Y while Blender's is -Y (the determinant -1 basis, issue #935).
Author through `Exterior.y()`, which converts a runtime lane position into the
Blender Y this scene is built in, so the export mirror puts it back exactly
where the map says it is.

The `.blend` a recipe writes is SOURCE AUTHORITY: `interior.save_source_blend`
refuses to overwrite one that exists, because ordinary work must never discard
hand-authoring.

**There is deliberately no worked example.** This module ships as a vocabulary
with no recipe calling it, because the one screen built to derive it was not
good enough to stand as a template, and a brief's worked example is what the
next author copies -- PRs #941 and #942 converged on one identical room for
exactly that reason. Read `docs/design/st-maria-exterior-authoring.md` for the
measured constants and the rules; then compose from the vocabulary rather than
adapting somebody else's street.
"""

from __future__ import annotations

import contextlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import second_rite_asset_core as asset_core  # noqa: E402
from first_stratum.common import box  # noqa: E402
from interior import (  # noqa: E402
    camera_record, emissive, floor_edge_x, half_width_at, material,
    native_y_at,
)

# The ground leaves the frame here; anything nearer the lens is off-screen.
FRAME_BOTTOM_NATIVE_Y = 240.0
# Rows below this are behind the translucent status menu.
DOCK_TOP_NATIVE_Y = 144.0
# The lowest scanline a character may stand on; the walker's feet land on 128.
CHARACTER_FLOOR_LIMIT = 144.0


def dock_cover_height(x, record=None):
    """Height above the ground an object at depth `x` needs to reach row 144.

    This is the whole arithmetic of the foreground band. It falls off fast with
    depth -- 1.09 m at X = -11, 0.64 m at X = -8, 0.03 m at X = -4 -- which is
    why a street's near layer is barrels and low walls rather than towers: the
    band only has to reach the top of the menu, not the top of the screen.
    """
    record = record or camera_record()
    lo, hi = 0.0, 24.0
    for _ in range(64):
        mid = (lo + hi) / 2.0
        if native_y_at(x, mid, record) > DOCK_TOP_NATIVE_Y:
            lo = mid
        else:
            hi = mid
    return hi


class Exterior:
    """One outdoor screen, built from the shared vocabulary.

    `span` is the runtime lane length; the scene is authored centred on the
    lane's midpoint so the export mirror is the same reflection the interiors
    already use.
    """

    def __init__(self, asset_id, span, *, back_x=9.0, near_x=-9.0,
                 ground_thick=0.6, margin=6.0):
        asset_core.reset_scene()
        self.asset_id = asset_id
        self.record = camera_record()
        self.span = float(span)
        self.lane_centre = self.span / 2.0
        # Where the ground plane leaves the bottom of the frame.
        self.front_x, _ = floor_edge_x(FRAME_BOTTOM_NATIVE_Y, self.record)
        self.back_x = float(back_x)
        self.near_x = float(near_x)
        self.ground_thick = float(ground_thick)
        self.margin = float(margin)
        self.parts = []
        self.foreground_parts = []
        self._registering = True
        self.lift = 0.0

        self.root = bpy.data.objects.new(asset_id.upper(), None)
        bpy.context.collection.objects.link(self.root)
        self.root.empty_display_type = "PLAIN_AXES"

        self.whitewash = material("whitewash")
        self.azulejo = material("azulejo")
        self.terracotta = material("terracotta")
        self.roof_tile = material("roof_tile")
        self.wood = material("dark_wood")
        self.stone = material("rough_limestone")
        self.paving = material("old_limestone")
        self.iron = material("wrought_iron")
        self.cloth = material("aged_cloth")
        self.crock = material("bone")
        self.straw = material("wax")
        self.foliage = material("foliage")
        self.glass = material("smoked_glass")
        self.lamplight = emissive("sr_lamp_glow", (0.46, 0.28, 0.13))
        self.window_glow = emissive("sr_window_daylight", (0.92, 0.95, 1.0))

    # -- lane -------------------------------------------------------------
    def y(self, lane_y):
        """Runtime lane position -> Blender Y in this scene."""
        return self.lane_centre - float(lane_y)

    # -- vegetation -------------------------------------------------------
    # Real leaf geometry, because a textured sphere is a sphere wearing a grass
    # coat. What makes planting read is the SILHOUETTE -- a ragged, serrated,
    # broken outline -- and no amount of surface texture supplies one. So this
    # builds actual blades and leaves, and uses `blob()` only as the dark
    # interior mass they sit on.
    #
    # Randomness is a deterministic LCG rather than `random`, because a recipe
    # must rebuild the same scene every time or the .blend stops being a
    # reproducible source.

    @staticmethod
    # -- vegetation: CARDS ------------------------------------------------
    # Retro vegetation is not modelled leaf by leaf. It is a handful of quads,
    # each carrying a cutout texture of a whole leaf CLUSTER with its twigs,
    # arranged as crossed planes for a tree and over a dome for a bush. The
    # mesh gives the silhouette and the parallax; the texture gives every leaf.
    #
    # Building real leaf geometry instead produced 8,751 objects for one hedge
    # and still read as boulders wearing spikes, which is the whole lesson.
    #
    # Randomness is a deterministic LCG rather than `random`, because a recipe
    # must rebuild the same scene every time or the .blend stops being a
    # reproducible source.

    @staticmethod
    def _rng(seed):
        state = [(int(seed) * 1103515245 + 12345) & 0x7FFFFFFF]

        def nxt(lo=0.0, hi=1.0):
            state[0] = (state[0] * 1103515245 + 12345) & 0x7FFFFFFF
            return lo + (hi - lo) * (state[0] / float(0x7FFFFFFF))
        return nxt

    def card_material(self):
        """The cutout material every foliage card shares.

        Alpha is wired straight from the sheet, so the quad disappears wherever
        the cluster does. Double-sided on purpose: a card is seen from both
        sides as the camera pans, and backface culling would blink half a bush
        out of existence.
        """
        if getattr(self, "_card_mat", None) is not None:
            return self._card_mat
        sheet = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                 / "materials" / "foliage_card")
        record = json.loads(
            (sheet / "material.json").read_text(encoding="utf-8"))
        self.card_names = record.get("cards") or ["broadleaf"]
        mat = bpy.data.materials.new("sr_foliage_card")
        mat.use_nodes = True
        mat.use_backface_culling = False
        tree = mat.node_tree
        bsdf = tree.nodes["Principled BSDF"]
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(sheet / "albedo.png"),
                                         check_existing=True)
        tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        bsdf.inputs["Roughness"].default_value = 0.92
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.05
        # A trace of emission keeps alpha cards legible when a branch turns
        # away from the key light; the sun/sky still supplies the dominant
        # shading and colour variation.
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (0.025, 0.045, 0.02, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.35
        self._card_mat = mat
        return mat

    def card(self, name, kind, size, location, *, rotation=(0.0, 0.0, 0.0),
             normal=None):
        """One foliage card: a quad UV-mapped to one cluster on the sheet.

        `normal`, when given, is written as a CUSTOM SPLIT NORMAL on all four
        corners. This is the trick that separates foliage from stuck-on paper:
        lit by its own flat quad normal, every card in a bush shades as a
        separate slab and the cluster reads as cardboard. Pointed outward from
        the mass instead -- as though it were the surface of a sphere -- the
        cards light together as one volume.
        """
        material = self.card_material()
        index = self.card_names.index(kind) if kind in self.card_names else 0
        count = max(1, len(self.card_names))
        u0, u1 = index / float(count), (index + 1) / float(count)
        width, height = float(size[0]), float(size[1])
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata([(-width / 2, 0.0, -height / 2),
                          (width / 2, 0.0, -height / 2),
                          (width / 2, 0.0, height / 2),
                          (-width / 2, 0.0, height / 2)], [], [(0, 1, 2, 3)])
        mesh.update()
        uv = mesh.uv_layers.new(name="UVMap")
        for loop_index, coord in enumerate(((u0, 0.0), (u1, 0.0),
                                            (u1, 1.0), (u0, 1.0))):
            uv.data[loop_index].uv = coord
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        asset_core.parent_local(obj, self.root, loc=location, rot=rotation)
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        if normal is not None:
            try:
                mesh.normals_split_custom_set([tuple(normal)] * 4)
            except (RuntimeError, TypeError):
                pass
        self.parts.append(obj)
        return obj

    def card_shell(self, name, centre, extent, *, count=14, kind="broadleaf",
                   card=0.9, seed=3, bias=0.5):
        """Clothe a mass in outward-facing cards laid over its dome.

        Each card sits on the ellipsoid surface, faces along its own outward
        normal, and CARRIES that normal for shading, so the shell lights as one
        volume. Directions pointing away from the lens are discarded -- `bias`
        is the most positive X a kept normal may have, and X is camera depth --
        because the far side is never seen and every card there is waste.
        """
        cx, cy, cz = centre
        ex, ey, ez = extent
        nxt = self._rng(seed)
        first, placed, guard = None, 0, 0
        while placed < int(count) and guard < int(count) * 16:
            guard += 1
            dx, dy, dz = nxt(-1.0, 1.0), nxt(-1.0, 1.0), nxt(-0.35, 1.0)
            norm = math.sqrt(dx * dx + dy * dy + dz * dz)
            if norm < 1e-3:
                continue
            dx, dy, dz = dx / norm, dy / norm, dz / norm
            if dx > bias:
                continue
            size = card * nxt(0.72, 1.3)
            obj = self.card("%s_card_%d" % (name, placed), kind,
                            (size, size * nxt(0.78, 1.05)),
                            (cx + dx * ex * 0.5, cy + dy * ey * 0.5,
                             cz + dz * ez * 0.5),
                            rotation=(nxt(-0.25, 0.25), nxt(-0.45, 0.45),
                                      nxt(-0.4, 0.4)),
                            normal=(dx, dy, dz))
            first = first or obj
            # EVERY card registers, not just the first. A shell that registered
            # only one representative hid a real violation: 1.6 m cards at the
            # near rank swallowed the character whole and `boards()` stayed
            # empty, because the thing it was measuring was the little lump
            # inside. One card is the right unit for the tall-or-continuous
            # rule anyway -- it is one occluding shape.
            self._register(obj)
            placed += 1
        return first

    def palm(self, name, lane_y, *, x=None, trunk_height=3.0, fronds=7,
             frond_length=2.2, lean=0.06, seed=1):
        """A palm: tapered leaning trunk and a crown of frond CARDS.

        Shaped to the tall-or-continuous rule by construction. The trunk is a
        POLE through the character's rows, and the crown -- the only wide part
        of the silhouette -- sits above head height, so the player is never
        swallowed.
        """
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        nxt = self._rng(seed)
        drums = 5
        for index in range(drums):
            t = index / float(drums)
            width = 0.30 * (1.0 - 0.32 * t)
            self.part("%s_trunk_%d" % (name, index),
                      (width, width, trunk_height / drums * 1.04),
                      (px + lean * trunk_height * t * t, cy + lean * 0.4 * t,
                       trunk_height * (t + 0.5 / drums)), self.wood)
        crown_x = px + lean * trunk_height
        crown_y = cy + lean * 0.4
        first = None
        for index in range(int(fronds)):
            yaw = (2.0 * math.pi * index / float(fronds)) + nxt(-0.2, 0.2)
            length = frond_length * nxt(0.85, 1.12)
            droop = nxt(-0.55, -0.12)
            obj = self.card("%s_frond_%d" % (name, index), "palm_frond",
                            (length, length * 0.72),
                            (crown_x + math.cos(yaw) * length * 0.28,
                             crown_y + math.sin(yaw) * length * 0.28,
                             trunk_height + 0.1 + droop * length * 0.2),
                            rotation=(droop, nxt(-0.15, 0.15), yaw),
                            normal=(0.0, 0.0, 1.0))
            first = first or obj
        self._register(first)
        return first

    def blob(self, name, size, location, mat, *, subdivisions=3,
             rotation=(0.0, 0.0, 0.0), smooth=True):
        """A soft lump. The vocabulary's only non-box primitive.

        Planting cannot be built from cubes. A box of leaf material reads as a
        painted slab, and at the 2x magnification of the near rank it reads as
        a slab two metres across -- which is how the first pass at this layer
        failed. What foliage needs is a silhouette with no straight edges and
        no canonical size, and an icosphere has one.

        **SMOOTH-SHADED, and this is not a detail.** The rest of this
        vocabulary is flat-shaded because it is architecture: a box wants its
        facets, and `flat_shade` is what keeps a wall reading as masonry. Leaf
        mass is the opposite -- faceted, it reads as a cut gem or a low-poly
        rock, which is exactly the thing planting was added to avoid. It also
        subdivides one step further than the boxes for the same reason: the
        silhouette is the whole point, and at 2 subdivisions the outline is
        still visibly a polygon.
        """
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=int(subdivisions),
                                              radius=0.5)
        obj = bpy.context.object
        obj.name = name
        obj.scale = tuple(float(v) for v in size)
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        x, y, z = location
        asset_core.parent_local(obj, self.root, loc=(x, y, z + self.lift),
                                rot=rotation)
        asset_core.assign_material(obj, mat)
        if smooth:
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
        else:
            asset_core.flat_shade(obj)
        self.parts.append(obj)
        return obj


    def hedge(self, name, lane_from, lane_to, *, x=None, height=0.72,
              depth=0.9, seed=0, kind="bush_mass", overlap=0.62, rows=2):
        """A low continuous run of planting, built from CARDS.

        The SKIRT case the house rule allows: wide, continuous, and low enough
        to hide the characters' feet without swallowing them.

        **A row of camera-facing cards, not a dome scatter.** Scattering sprig
        cards over an ellipsoid is how you build a shrub; a hedge is a wall of
        foliage, and the card that makes one is a whole hedge SECTION -- domed
        top, ragged edge, wider than tall. Laid overlapping along the lane they
        merge into a continuous run whose outline never repeats. Scattered
        instead, the same cards read as clumps of tall grass, which is what
        three earlier passes produced.

        `rows` places a second rank further from the lens and slightly higher,
        so the run has depth rather than reading as one flat billboard, and the
        gaps in the front rank show planting behind rather than the street.
        """
        px = self.near_x if x is None else float(x)
        y0, y1 = sorted((self.y(lane_from), self.y(lane_to)))
        run = y1 - y0
        width = height * 1.9
        step = width * overlap
        count = max(2, int(round(run / step)))
        nxt = self._rng(seed + 7)
        first = None
        for rank in range(max(1, int(rows))):
            # Back ranks sit deeper and a little taller, and are offset by half
            # a step so their seams never line up with the front rank's.
            back = rank / float(max(1, rows))
            rx = px + depth * 0.55 * back
            lift = 1.0 + 0.16 * back
            offset = step * 0.5 * rank
            for index in range(count + rank):
                cy = y0 + offset + run * (index + 0.5) / count
                if cy > y1 + step * 0.5:
                    continue
                size = width * nxt(0.86, 1.18)
                card = self.card(
                    "%s_r%d_%d" % (name, rank, index), kind,
                    (size, size * nxt(0.52, 0.68) * lift),
                    (rx + nxt(-0.06, 0.06), cy,
                     height * 0.5 * lift * nxt(0.92, 1.1)),
                    # MINUS pi/2, and the sign is load-bearing. The card
                    # quad's own normal is local -Y; +pi/2 turns it to +X,
                    # which points AWAY from the lens. Cycles then flips the
                    # shading normal on that backface, so the skyward normal
                    # below arrived pointing at the ground and the whole run
                    # rendered black. Facing the quad at the camera means no
                    # flip happens and the transferred normal survives.
                    rotation=(nxt(-0.06, 0.06), nxt(-0.05, 0.05),
                              -math.pi / 2.0 + nxt(-0.22, 0.22)),
                    # Mostly UP, in LOCAL space -- custom split normals are
                    # stored before the object rotation, and Rz(-90) maps this
                    # to a world normal of about (-0.38, 0, 0.92). The normal a
                    # card carries should be the normal of the VOLUME it stands
                    # in for, and the top of a hedge faces the sky.
                    normal=(0.0, -0.38, 0.92))
                first = first or card
                if rank == 0:
                    self._register(card)
        return first

    def part(self, name, size, location, mat, **kw):
        x, y, z = location
        obj = box(name, self.root, size, (x, y, z + self.lift), mat,
                  asset_core, **kw)
        self.parts.append(obj)
        return obj

    # -- ground -----------------------------------------------------------
    def ground(self, *, name="ground", material_value=None, levels=()):
        """The paved street, from the frame bottom back past the facades.

        `levels` is an optional list of (lane_from, lane_to, dz) raised aprons
        -- a step up to a chapel forecourt, a quay edge. They change where the
        ground is DRAWN; the lane's own `groundProfile` is what the player
        walks, and the two are authored to agree.
        """
        depth = (self.back_x + self.margin) - self.front_x
        centre_x = self.front_x + depth / 2.0
        length = self.span + 2.0 * self.margin
        slab = self.part(name, (depth, length, self.ground_thick),
                         (centre_x, 0.0, -self.ground_thick / 2.0),
                         material_value or self.paving)
        for index, (lane_from, lane_to, dz) in enumerate(levels):
            run = abs(self.y(lane_to) - self.y(lane_from))
            mid = (self.y(lane_from) + self.y(lane_to)) / 2.0
            self.part("%s_apron_%d" % (name, index),
                      (depth, run, abs(dz) + 0.05),
                      (centre_x, mid, (float(dz) - 0.05) / 2.0),
                      material_value or self.paving)
        return slab

    # -- the far side -----------------------------------------------------
    def facade(self, name, lane_y, *, width, height, depth=3.4, x=None,
               material_value=None, roof=True, eaves=0.55,
               dado=False, plinth=0.35):
        """One building mass on the far side of the street.

        `x` staggers a building forward or back out of the terrace line, which
        is the main axis of variation available here: rooflines are OUT OF
        FRAME by construction at this camera, so height differences are
        invisible and depth differences are not.
        """
        base_x = self.back_x if x is None else float(x)
        cy = self.y(lane_y)
        wall = self.part(name, (depth, width, height),
                         (base_x + depth / 2.0, cy, height / 2.0),
                         material_value or self.whitewash)
        if plinth:
            self.part("%s_plinth" % name, (depth + 0.12, width + 0.12, plinth),
                      (base_x + depth / 2.0, cy, plinth / 2.0), self.stone)
        if dado:
            self.part("%s_dado" % name, (0.08, width, 0.95),
                      (base_x - 0.04, cy, 0.95 / 2.0 + plinth), self.azulejo)
        if roof:
            self.part("%s_eaves" % name, (depth + eaves, width + eaves, 0.4),
                      (base_x + depth / 2.0, cy, height + 0.2), self.terracotta)
        return wall

    def gable_roof(self, name, lane_y, *, width, depth, eave_z,
                   rise=2.0, x=None, overhang=0.3,
                   material_value=None, ridge_offset=0.0):
        """A true pitched roof prism, expressed as an editable cross-section.

        The owner's Praca studies establish the useful vocabulary here: a
        ridge parallel to the street, small masonry-clearing overhangs, and a
        roof that remains independent from the wall mass.  ``ridge_offset``
        moves the peak in depth without scaling either slope, so lean-tos and
        unequal colonial roof pitches are ordinary recipe parameters.
        """
        base_x = self.back_x if x is None else float(x)
        cy = self.y(lane_y)
        half_y = float(width) / 2.0 + float(overhang)
        front = base_x - float(overhang)
        back = base_x + float(depth) + float(overhang)
        ridge_x = (front + back) / 2.0 + float(ridge_offset)
        z0 = float(eave_z)
        z1 = z0 + float(rise)
        vertices = [
            (front, cy - half_y, z0), (front, cy + half_y, z0),
            (ridge_x, cy - half_y, z1), (ridge_x, cy + half_y, z1),
            (back, cy - half_y, z0), (back, cy + half_y, z0),
        ]
        faces = [(0, 1, 3, 2), (2, 3, 5, 4), (0, 2, 4), (1, 5, 3)]
        mesh = bpy.data.meshes.new("%s_mesh" % name)
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(material_value or self.roof_tile)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = self.root
        self.parts.append(obj)
        return obj

    def doorway(self, name, lane_y, *, width=1.15, height=2.25, x=None,
                lintel=True, lamp=False):
        """A panelled door in a facade, centred on a runtime lane position.

        The door is the anchor: a runtime doorway names a lane Y, and this puts
        the picture of a door at exactly that Y, so what the player sees and
        what the provider tests are the same place.
        """
        base_x = self.back_x if x is None else float(x)
        cy = self.y(lane_y)
        # Construct the surround from separate members.  A solid slab behind
        # the leaf reads as a pasted-on rectangle; jambs and a recessed leaf
        # give the same layered depth as the owner's authored openings.
        leaf = self.part("%s_leaf" % name, (0.12, width, height),
                         (base_x - 0.015, cy, height / 2.0), self.wood)
        jamb = 0.18
        projection = 0.16
        for side, tag in ((-1, "l"), (1, "r")):
            self.part("%s_jamb_%s" % (name, tag),
                      (projection, jamb, height + 0.18),
                      (base_x - projection / 2.0 - 0.04,
                       cy + side * (width / 2.0 + jamb / 2.0),
                       (height + 0.18) / 2.0), self.stone)
        self.part("%s_threshold" % name, (0.52, width + 0.42, 0.16),
                  (base_x - 0.22, cy, 0.08), self.stone)
        if lintel:
            self.part("%s_lintel" % name, (projection + 0.1, width + 0.5, 0.24),
                      (base_x - projection / 2.0 - 0.08, cy,
                       height + 0.12), self.stone)
            self.part("%s_drip" % name, (projection + 0.18, width + 0.68, 0.1),
                      (base_x - projection / 2.0 - 0.13, cy,
                       height + 0.29), self.terracotta)
        if lamp:
            spot = (base_x - 0.3, cy + width / 2.0 + 0.3, height + 0.5)
            self.part("%s_lamp" % name, (0.22, 0.22, 0.3), spot,
                      self.lamplight)
            self.lamp_light("%s_lamp_source" % name, spot)
        return leaf

    def window(self, name, lane_y, *, width=0.95, height=1.25, sill_z=1.15,
               x=None, shutters=True, grille=False, lit=False):
        base_x = self.back_x if x is None else float(x)
        cy = self.y(lane_y)
        pane = self.part("%s_pane" % name, (0.08, width, height),
                         (base_x - 0.015, cy, sill_z + height / 2.0),
                         self.window_glow if lit else self.glass)
        surround = 0.14
        for side, tag in ((-1, "l"), (1, "r")):
            self.part("%s_jamb_%s" % (name, tag),
                      (0.16, surround, height + 0.22),
                      (base_x - 0.1,
                       cy + side * (width / 2.0 + surround / 2.0),
                       sill_z + height / 2.0), self.stone)
        self.part("%s_head" % name, (0.18, width + 0.42, 0.16),
                  (base_x - 0.11, cy, sill_z + height + 0.11), self.stone)
        self.part("%s_sill" % name, (0.38, width + 0.46, 0.14),
                  (base_x - 0.16, cy, sill_z - 0.07), self.stone)
        # A small wood frame and mullion keep the pane from reading as a black
        # void at native resolution.
        self.part("%s_frame_top" % name, (0.1, width, 0.08),
                  (base_x - 0.08, cy, sill_z + height - 0.04), self.wood)
        self.part("%s_frame_bottom" % name, (0.1, width, 0.08),
                  (base_x - 0.08, cy, sill_z + 0.04), self.wood)
        self.part("%s_mullion" % name, (0.1, 0.07, height),
                  (base_x - 0.08, cy, sill_z + height / 2.0), self.wood)
        if shutters:
            for side, tag in ((-1, "l"), (1, "r")):
                self.part("%s_shutter_%s" % (name, tag),
                          (0.08, width * 0.52, height),
                          (base_x - 0.16, cy + side * (width * 0.76),
                           sill_z + height / 2.0), self.wood)
        if grille:
            self.part("%s_grille" % name, (0.06, width + 0.1, height + 0.1),
                      (base_x - 0.2, cy, sill_z + height / 2.0), self.iron)
        return pane

    # -- the near side ----------------------------------------------------
    def foreground(self, name, lane_y, *, size, x=None, material_value=None,
                   z=None, rotation=(0, 0, 0)):
        """One near-camera occluder, in front of the action plane.

        Registered separately so `dock_coverage` can report how much of the
        translucent menu band this screen actually covers -- the number that
        decides whether the near layer is doing its job.
        """
        px = self.near_x if x is None else float(x)
        base_z = (float(size[2]) / 2.0) if z is None else float(z)
        obj = self.part(name, size, (px, self.y(lane_y), base_z),
                        material_value or self.stone, rotation=rotation)
        self._register(obj)
        return obj

    def awning(self, name, lane_y, *, width=2.6, x=None, z=2.05,
               drop=0.45, material_value=None):
        """A cloth awning reaching out from the far side over the street."""
        base_x = self.back_x if x is None else float(x)
        cy = self.y(lane_y)
        cloth = material_value or self.cloth
        self.part("%s_cloth" % name, (1.7, width, 0.09),
                  (base_x - 0.9, cy, z), cloth,
                  rotation=(0.0, math.radians(9.0), 0.0))
        self.part("%s_valance" % name, (0.09, width, drop),
                  (base_x - 1.72, cy, z - drop / 2.0), cloth)
        for side, tag in ((-1, "l"), (1, "r")):
            self.part("%s_stay_%s" % (name, tag), (1.6, 0.07, 0.07),
                      (base_x - 0.9, cy + side * width / 2.0, z - 0.06),
                      self.iron)

    def stall(self, name, lane_y, *, width=2.2, x=None, height=0.92,
              canopy=True):
        """A market trestle: the stall a commercial street is built from."""
        px = (self.back_x - 2.6) if x is None else float(x)
        cy = self.y(lane_y)
        self.part("%s_board" % name, (1.25, width, 0.1), (px, cy, height),
                  self.wood)
        for leg, (dx, dy) in enumerate(
                ((-0.5, -width / 2.0 + 0.16), (-0.5, width / 2.0 - 0.16),
                 (0.5, -width / 2.0 + 0.16), (0.5, width / 2.0 - 0.16))):
            self.part("%s_leg_%d" % (name, leg), (0.1, 0.1, height),
                      (px + dx, cy + dy, height / 2.0), self.wood)
        if canopy:
            self.part("%s_canopy" % name, (1.7, width + 0.3, 0.08),
                      (px, cy, height + 1.18), self.cloth,
                      rotation=(0.0, math.radians(7.0), 0.0))
            for post, dy in enumerate((-width / 2.0, width / 2.0)):
                self.part("%s_post_%d" % (name, post),
                          (0.08, 0.08, height + 1.18),
                          (px + 0.6, cy + dy, (height + 1.18) / 2.0), self.wood)

    def crate(self, name, lane_y, *, x=None, size=(0.7, 0.7, 0.6), z=None):
        return self.foreground(name, lane_y, size=size, x=x,
                               material_value=self.wood, z=z)

    def barrel(self, name, lane_y, *, x=None, radius=0.42, height=0.95):
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        obj = self.part(name, (radius * 2, radius * 2, height),
                        (px, cy, height / 2.0), self.wood)
        for hoop, band_z in enumerate((height * 0.24, height * 0.76)):
            self.part("%s_hoop_%d" % (name, hoop),
                      (radius * 2.08, radius * 2.08, 0.07), (px, cy, band_z),
                      self.iron)
        self._register(obj)
        return obj

    def planter(self, name, lane_y, *, x=None, height=0.62, spread=1.15,
                clumps=4, kind="sprig"):
        """Terracotta pot and its planting, the planting being cards."""
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        pot = self.part("%s_pot" % name, (0.78, 0.78, height),
                        (px, cy, height / 2.0), self.terracotta)
        self.card_shell("%s_shell" % name, (px, cy, height + spread * 0.34),
                        (spread * 0.8, spread, spread * 0.8),
                        count=int(clumps), kind=kind, card=spread * 0.95,
                        seed=int(abs(lane_y) * 7) + 3)
        self._register(pot)
        return pot

    def handcart(self, name, lane_y, *, x=None, length=2.1, height=0.78,
                 tipped=False):
        """A two-wheeled handcart left standing in the street.

        The near band's workhorse: it is tall enough to cover the menu band,
        open enough to see the street through, and it reads as something a
        person put there this morning rather than as masonry.
        """
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        tilt = math.radians(16.0) if tipped else 0.0
        bed = self.part("%s_bed" % name, (0.96, length, 0.16),
                        (px, cy, height), self.wood, rotation=(tilt, 0.0, 0.0))
        for side, tag in ((-1, "l"), (1, "r")):
            self.part("%s_side_%s" % (name, tag), (0.1, length, 0.34),
                      (px + side * 0.44, cy, height + 0.17), self.wood)
        for wheel, dy in enumerate((-length * 0.22, length * 0.22)):
            self.part("%s_wheel_%d" % (name, wheel), (0.66, 0.12, 0.66),
                      (px + 0.1, cy + dy, 0.33), self.wood)
            self.part("%s_hub_%d" % (name, wheel), (0.2, 0.16, 0.2),
                      (px + 0.1, cy + dy, 0.33), self.iron)
        for shaft, dy in enumerate((-0.3, 0.3)):
            self.part("%s_shaft_%d" % (name, shaft), (0.09, 1.15, 0.09),
                      (px - 0.1, cy + dy + length * 0.62, height - 0.1),
                      self.wood, rotation=(math.radians(-9.0), 0.0, 0.0))
        self._register(bed)
        return bed

    def stack(self, name, lane_y, *, x=None, count=3, unit=(0.72, 0.78, 0.52),
              jitter=0.13, material_value=None):
        """A leaning stack of crates or bales.

        `jitter` offsets each course so the tower is not a single extruded
        column -- the same reason the parapet had to be broken into runs.
        """
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        mat = material_value or self.wood
        base = None
        for index in range(int(count)):
            sway = jitter * (1 if index % 2 else -1) * (index / max(count - 1, 1))
            obj = self.part("%s_%d" % (name, index), unit,
                            (px + sway * 0.6, cy + sway,
                             unit[2] * (index + 0.5)), mat,
                            rotation=(0.0, 0.0, math.radians(9.0 * index)))
            base = base or obj
        self._register(base)
        return base

    def sacks(self, name, lane_y, *, x=None, count=3, height=0.52):
        """Slumped grain sacks: low, soft, and good at filling the gap between
        two taller near pieces without adding another hard silhouette."""
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        first = None
        spread = ((0.0, 0.0, 1.0), (-0.34, 0.42, 0.84), (0.3, -0.38, 0.9),
                  (0.05, 0.72, 0.76))
        for index in range(min(int(count), len(spread))):
            dx, dy, scale = spread[index]
            obj = self.part("%s_%d" % (name, index),
                            (0.62 * scale, 0.78 * scale, height * scale),
                            (px + dx, cy + dy, height * scale / 2.0),
                            self.cloth,
                            rotation=(0.0, 0.0, math.radians(24.0 * index)))
            first = first or obj
        self._register(first)
        return first

    def net_rack(self, name, lane_y, *, x=None, height=2.4, width=2.2,
                 strips=3):
        """Fishing nets hung to dry on a frame -- the Quay end of a street.

        Hung as SEPARATE STRIPS rather than one sheet, and that is the rule
        rather than a detail. One drape this size is tall *and* continuous: a
        board that swallows the whole character. Strips keep the height, drop
        the continuity, and the player stays readable through the gaps.
        """
        px = self.near_x if x is None else float(x)
        cy = self.y(lane_y)
        for post, dy in enumerate((-width / 2.0, width / 2.0)):
            self.part("%s_post_%d" % (name, post), (0.13, 0.13, height),
                      (px, cy + dy, height / 2.0), self.wood)
        self.part("%s_rail" % name, (0.1, width + 0.2, 0.1),
                  (px, cy, height), self.wood)
        count = max(1, int(strips))
        pitch = width / float(count)
        first = None
        for index in range(count):
            dy = -width / 2.0 + pitch * (index + 0.5)
            drop = height * (0.58 if index % 2 == 0 else 0.44)
            strip = self.part("%s_net_%d" % (name, index),
                              (0.07, pitch * 0.5, drop),
                              (px + 0.06, cy + dy, height - drop / 2.0),
                              self.cloth)
            first = first or strip
        self._register(first)
        return first

    def low_wall(self, name, lane_from, lane_to, *, x=None, height=0.95,
                 thick=0.42, coping=True):
        """A run of parapet along the near side -- the band's connective
        tissue, and what makes the separate props read as one street edge."""
        px = self.near_x if x is None else float(x)
        run = abs(self.y(lane_to) - self.y(lane_from))
        mid = (self.y(lane_from) + self.y(lane_to)) / 2.0
        obj = self.part(name, (thick, run, height), (px, mid, height / 2.0),
                        self.stone)
        if coping:
            self.part("%s_coping" % name, (thick + 0.16, run, 0.12),
                      (px, mid, height + 0.06), self.paving)
        self._register(obj)
        return obj

    # -- light ------------------------------------------------------------
    def sky_rig(self, *, dome_energy=42.0, sun_energy=1.5,
                dome_colour=(0.55, 0.68, 0.86), sun_colour=(1.0, 0.95, 0.86),
                sun_angle_deg=52.0):
        """The exterior light: a big soft sky, one weak sun for direction.

        Deliberately NOT the interior rig. Indoors a hard key reads as a
        diorama; outdoors the absence of any direction reads as fog. The sun is
        kept weak relative to the dome so the street gains a direction without
        the harsh cast shadows the albedo doctrine keeps out of the textures.
        """
        dome = bpy.data.lights.new("%s_SKY" % self.asset_id, type="AREA")
        dome.energy = float(dome_energy) * max(self.span, 8.0)
        dome.shape = "RECTANGLE"
        dome.size = 24.0
        dome.size_y = self.span + 2.0 * self.margin
        dome.color = dome_colour
        obj = bpy.data.objects.new("%s_SKY" % self.asset_id, dome)
        obj.location = (self.front_x + 6.0, 0.0, 16.0)
        bpy.context.collection.objects.link(obj)

        sun = bpy.data.lights.new("%s_SUN" % self.asset_id, type="SUN")
        sun.energy = float(sun_energy)
        sun.color = sun_colour
        sun.angle = math.radians(6.0)
        sun_obj = bpy.data.objects.new("%s_SUN" % self.asset_id, sun)
        sun_obj.rotation_euler = (math.radians(sun_angle_deg), 0.0,
                                  math.radians(-34.0))
        bpy.context.collection.objects.link(sun_obj)
        return obj, sun_obj

    def lamp_light(self, name, location, *, energy=14.0,
                   colour=(1.0, 0.68, 0.36)):
        data = bpy.data.lights.new(name, type="POINT")
        data.energy = float(energy)
        data.color = colour
        data.shadow_soft_size = 0.22
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.collection.objects.link(obj)
        return obj

    # -- measurement ------------------------------------------------------
    def dock_coverage(self, lane_y, *, samples=96):
        """Fraction of the menu band (rows 144-240) the near layer covers at
        one lane position.

        Because the camera pans, the answer is per-position and an average over
        the whole lane would hide a hole. Approximate on purpose: it rasterises
        each foreground part's projected bounding box rather than its
        silhouette, which is the right precision for deciding whether a band
        exists at all.
        """
        bpy.context.view_layer.update()
        centre = self.y(lane_y)
        record = self.record
        half = half_width_at(0.0 - record["eye"]["x"], record)
        covered = [False] * samples
        step = (FRAME_BOTTOM_NATIVE_Y - DOCK_TOP_NATIVE_Y) / samples
        for obj in self.foreground_parts:
            origin = obj.matrix_world.translation
            dims = obj.dimensions
            near_x = origin.x - dims.x / 2.0
            top_z = origin.z + dims.z / 2.0
            y_lo, y_hi = origin.y - dims.y / 2.0, origin.y + dims.y / 2.0
            if y_hi - centre < -half or y_lo - centre > half:
                continue
            try:
                top_row = native_y_at(near_x, top_z, record)
                base_row = native_y_at(near_x, 0.0, record)
            except ValueError:
                continue
            for index in range(samples):
                row = DOCK_TOP_NATIVE_Y + (index + 0.5) * step
                if top_row <= row <= base_row:
                    covered[index] = True
        return sum(1 for hit in covered if hit) / float(samples)


    # -- layers -----------------------------------------------------------
    # The near stack is not one thing. Ordered by distance from the lens:
    #
    #   NEAR         the foreground's foreground. It occludes the foreground
    #                layer, and in any flattened presentation it parallaxes
    #                fastest. By default it does NOT occlude the player.
    #   FOREGROUND   the pass-behind layer: it DOES occlude the player, and
    #                that occlusion event is the whole reason it exists.
    #   PROP         street furniture at or behind the action plane, where an
    #                object of known size reads at its true size.
    #
    # Only the first two are measured, because only they are competing for the
    # menu band and the frame edge. A prop registered as near would quietly
    # inflate the coverage number and hide a real gap.

    @contextlib.contextmanager
    def props(self):
        """Build street furniture that is NOT part of the near stack."""
        previous = self._registering
        self._registering = False
        try:
            yield self
        finally:
            self._registering = previous

    def _register(self, obj):
        if self._registering:
            self.foreground_parts.append(obj)
        return obj

    @staticmethod
    def _world_box(obj):
        """World-space min/max of one object.

        `obj.dimensions` is the LOCAL bounding box scaled, which is wrong for
        anything rotated -- and a foliage card is built in its own XZ plane, so
        its width lives on local X and `dimensions.y` reads as zero. Measured
        that way every card scored as a zero-width pole and the tall-or-
        continuous guard waved through cards that swallowed the character.
        """
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
        return lo, hi

    def occludes_player(self, lane_y=None):
        """Near pieces that cross the player, classified by SHAPE.

        The house rule: an occluder may be **tall or continuous, but not
        both**. Foliage that hides the characters' feet across a good part of
        the screen is fine. A pole is fine. A large board that swallows the
        whole character is not -- the player loses track of where they are.

        So the two numbers that matter are how much of the CHARACTER a piece
        covers and how much of the FRAME WIDTH it spans, and the verdict is
        about their combination rather than either alone:

            pole        tall, narrow            fine
            skirt       wide, low               fine
            board       tall AND wide           REJECTED
            incidental  covers neither much     fine

        The walker occupies rows 80 (head) to 128 (feet).
        """
        bpy.context.view_layer.update()
        record = self.record
        head, feet = 80.0, 128.0
        span = feet - head
        rows = []
        for obj in self.foreground_parts:
            lo, hi = self._world_box(obj)
            near_x = lo[0]
            depth = near_x - record["eye"]["x"]
            if depth <= 1e-6:
                continue
            try:
                top_row = native_y_at(near_x, hi[2], record)
                base_row = native_y_at(near_x, lo[2], record)
            except ValueError:
                continue
            overlap = max(0.0, min(base_row, feet) - max(top_row, head))
            covers = overlap / span
            width = (hi[1] - lo[1]) / (2.0 * half_width_at(depth, record))
            if lane_y is not None:
                centre = (lo[1] + hi[1]) / 2.0
                if abs(centre - self.y(lane_y)) > (hi[1] - lo[1]) / 2.0 + 2.0:
                    continue
            if covers < 0.2 and width < 0.25:
                continue
            if covers >= 0.55 and width >= 0.25:
                verdict = "BOARD"
            elif width >= 0.25:
                verdict = "skirt"
            else:
                verdict = "pole"
            rows.append({"part": obj.name, "coversCharacter": round(covers, 3),
                         "frameWidth": round(width, 3), "shape": verdict})
        rows.sort(key=lambda row: (row["shape"] != "BOARD",
                                   -row["coversCharacter"]))
        return rows

    def boards(self):
        """Occluders that break the tall-or-continuous rule. Should be empty."""
        return [row for row in self.occludes_player() if row["shape"] == "BOARD"]

    def foreground_scale(self):
        """How much of the frame WIDTH each near piece occupies at its depth.

        The frame narrows fast toward the lens -- half-width is 4.67 m at the
        action plane but 1.92 m at X = -11 -- so a near object's readable size
        is set by where it stands, not by how big it is. A handcart that reads
        correctly at X = -7 covers half the screen at X = -11, and the mistake
        is invisible in the dock-coverage number, which only rewards covering
        more. Returns the worst offenders first.
        """
        bpy.context.view_layer.update()
        record = self.record
        rows = []
        for obj in self.foreground_parts:
            lo, hi = self._world_box(obj)
            depth = lo[0] - record["eye"]["x"]
            if depth <= 1e-6:
                continue
            frame_width = 2.0 * half_width_at(depth, record)
            rows.append((obj.name, round((hi[1] - lo[1]) / frame_width, 3),
                         round((lo[0] + hi[0]) / 2.0, 2)))
        rows.sort(key=lambda row: -row[1])
        return rows

    def bounds(self):
        bpy.context.view_layer.update()
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for obj in self.parts:
            for corner in obj.bound_box:
                point = obj.matrix_world @ Vector(corner)
                for axis in range(3):
                    lo[axis] = min(lo[axis], point[axis])
                    hi[axis] = max(hi[axis], point[axis])
        return lo, hi
