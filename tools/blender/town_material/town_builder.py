"""Phase 2/3: build a richly textured Second Gate side-view town.

Camera authority
----------------
The camera is NEVER authored here. It comes from the Thestra-generated
calibration (eye / lens / pitch / projection window) via ``thestra_camera``.
This module only decides where the town sits in front of it.

One consequence of that camera is worth stating explicitly. ``fovHalfX`` and
``fovHalfY`` are tangents, so the visible frame at distance d is
(2*0.25*d) x (2*0.140625*d). At the study's 6.9-unit framing distance a 1.7 m
person fills 88% of the frame height -- that distance was chosen to compare
lenses, not to stage a town. The action plane therefore sits near 18 units,
where a person reads at about a third of the frame height. The eye, lens and
pitch are untouched.

Collections
-----------
TH_SOURCE          rich, expensive, subdivided + displaced authoring geometry
TH_RENDER          coarse silhouette/occlusion geometry for the runtime
TH_COLLISION       collision volumes
TH_ANCHORS         doors, spawns, transition points
TH_PREVIEW_ACTORS  walker/NPC preview planes (never baked, never exported)
TH_PREVIEW_ONLY    staging helpers
TH_CAMERA_PREVIEW  the calibrated camera
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import materials as M  # noqa: E402
import proc_materials as P  # noqa: E402
import thestra_camera  # noqa: E402

ROOT = HERE.parents[2]
WALKER = ROOT / "projects/hichaukitoden-game/assets/character/walker.png"
PH = M.PH_DIR
GEN = M.GEN_DIR

COLLECTIONS = ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS",
               "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]

GROUND_Z = -1.70          # eye sits 1.70 above the street
ACTION_X = 19.0           # where actors walk; ~33% frame height for a 1.7m person
STREET_Y = 5.5            # camera is centred on this


# ------------------------------------------------------------------ scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        for d in prefs.get_devices_for_type("OPTIX"):
            d.use = True
    except Exception:
        pass
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"
    for name in COLLECTIONS:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
    return scene


def col(name):
    return bpy.data.collections[name]


def put(obj, name):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col(name).objects.link(obj)
    return obj


def _mesh_obj(name, verts, faces, collection):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return put(ob, collection)


def box(name, cx, cy, cz, sx, sy, sz, collection):
    """Axis-aligned box; x=depth from camera, y=street run, z=up."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    v = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
         (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
         (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
         (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    # Winding matters: these were all inward-facing in the first pass, which
    # rendered acceptably (Cycles flips normals for diffuse on backfaces) but
    # broke the selected-to-active bake -- rays cast along the target normal
    # went INTO each box and hit nothing, producing a 97%-empty black atlas.
    f = [(0, 3, 2, 1),   # -Z
         (4, 5, 6, 7),   # +Z
         (0, 1, 5, 4),   # -Y
         (1, 2, 6, 5),   # +X
         (2, 3, 7, 6),   # +Y
         (3, 0, 4, 7)]   # -X
    return _mesh_obj(name, v, f, collection)


def facade_panel(name, x, cy, cz, sy, sz, collection, subdiv=7):
    """A flat, densely subdivided panel facing the camera (-X).

    Displacement belongs on a panel like this, not on a box. Pushing a cube
    along its vertex normals moves adjacent faces in different directions and
    cracks the shared edges apart -- that is what produced the torn, black-
    mottled facades and the floating debris in the first pass. A single flat
    quad has one uniform normal, so relief stays watertight.
    """
    n = 2 ** subdiv
    verts, faces = [], []
    for j in range(n + 1):
        for i in range(n + 1):
            verts.append((x, cy - sy / 2 + sy * i / n, cz - sz / 2 + sz * j / n))
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            faces.append((a, a + 1, a + n + 2, a + n + 1))
    ob = _mesh_obj(name, verts, faces, collection)
    uv = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            co = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.y, co.z)
    for poly in ob.data.polygons:
        poly.flip()          # face the camera
    ob.data.update()
    return ob


def displace_panel(ob, height_png, strength=0.05):
    """Displace a flat panel; no subsurf needed, the panel is already dense."""
    tex = bpy.data.textures.new(ob.name + "_H", "IMAGE")
    tex.image = bpy.data.images.load(str(Path(height_png).resolve()), check_existing=True)
    tex.extension = "REPEAT"
    d = ob.modifiers.new("DISPLACE", "DISPLACE")
    d.texture = tex
    d.texture_coords = "UV"
    d.strength = strength
    d.mid_level = _height_midlevel(height_png)
    d.direction = "X"
    return ob


def uv_scale_panel(ob, scale):
    uv = ob.data.uv_layers["UVMap"]
    for d in uv.data:
        d.uv = (d.uv[0] * scale, d.uv[1] * scale)
    return ob


def uv_project(ob, scale=1.0, axis="facade"):
    """Cheap box-ish UV: facade faces use (y,z), ground uses (y,x)."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) > 0.7:               # horizontal face
                u, v = co.y, co.x
            elif abs(n.x) > 0.7:             # facade face
                u, v = co.y, co.z
            else:                            # side wall
                u, v = co.x, co.z
            uv.data[li].uv = (u * scale, v * scale)
    return ob


def displace(ob, height_png, strength=0.06, levels=5, midlevel=None):
    """TH_SOURCE relief: subdivide, then push by a real height map.

    ``midlevel`` defaults to the height map's own mean rather than 0.5. A scan
    height map is rarely centred on 0.5, so a fixed mid-level pushes the whole
    surface outward and the raised regions tear off the box as floating debris.
    """
    if midlevel is None:
        midlevel = _height_midlevel(height_png)
    sub = ob.modifiers.new("SUBSURF", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = levels
    tex = bpy.data.textures.new(ob.name + "_H", "IMAGE")
    tex.image = bpy.data.images.load(str(Path(height_png).resolve()), check_existing=True)
    tex.extension = "REPEAT"
    d = ob.modifiers.new("DISPLACE", "DISPLACE")
    d.texture = tex
    d.texture_coords = "UV"
    d.strength = strength
    d.mid_level = midlevel
    return ob


_MIDLEVEL_CACHE = {}


def _height_midlevel(path):
    """Mean luminance of a height map, so displacement is centred on it."""
    key = str(path)
    if key not in _MIDLEVEL_CACHE:
        img = bpy.data.images.load(str(Path(path).resolve()), check_existing=True)
        px = img.pixels[:]
        # sample sparsely; these are 2K maps and we only need the mean
        step = max(4, (len(px) // 4) // 20000) * 4
        vals = px[0::step]
        _MIDLEVEL_CACHE[key] = sum(vals) / max(len(vals), 1)
    return _MIDLEVEL_CACHE[key]


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


# ------------------------------------------------------------------ lighting
def light_rig(scene, spec):
    """Sun + sky + optional warm practicals. Real Blender lighting, no fakery."""
    sun_data = bpy.data.lights.new("SUN", "SUN")
    sun_data.energy = spec["sunEnergy"]
    sun_data.color = spec["sunColour"]
    sun_data.angle = math.radians(spec.get("sunSoftness", 2.0))
    sun = bpy.data.objects.new("SUN", sun_data)
    # elevation/azimuth chosen so the key rakes ACROSS the facades
    el, az = math.radians(spec["sunElevation"]), math.radians(spec["sunAzimuth"])
    sun.rotation_euler = (math.radians(90.0) - el, 0.0, az)
    scene.collection.objects.link(sun)
    put(sun, "TH_PREVIEW_ONLY")

    # A flat dark background renders as pure black wherever the street opens to
    # sky, which reads as a hole rather than as air. Give the sky a real
    # gradient: brighter and warmer near the horizon, deeper overhead.
    world = bpy.data.worlds.new("SKY")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = spec["skyStrength"]
    # For a world shader the Generated vector IS the view direction, so its Z
    # component is the elevation. A gradient texture with a rotated mapping
    # does not track that, which is why the first version rendered flat black.
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    elev = nt.nodes.new("ShaderNodeMapRange")
    elev.inputs["From Min"].default_value = -0.15
    elev.inputs["From Max"].default_value = 0.55
    elev.inputs["To Min"].default_value = 0.0
    elev.inputs["To Max"].default_value = 1.0
    elev.clamp = True
    nt.links.new(sep.outputs["Z"], elev.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    zc = spec["skyColour"]
    horizon = spec.get("skyHorizon", (min(zc[0] * 2.2 + 0.16, 1.0),
                                      min(zc[1] * 2.0 + 0.16, 1.0),
                                      min(zc[2] * 1.5 + 0.12, 1.0), 1.0))
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = tuple(horizon)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = tuple(zc)
    nt.links.new(elev.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], wout.inputs["Surface"])
    scene.world = world

    for i, (y, z, x, energy, colour) in enumerate(spec.get("practicals", [])):
        d = bpy.data.lights.new(f"PRACTICAL_{i}", "POINT")
        d.energy = energy
        d.color = colour
        d.shadow_soft_size = 0.25
        o = bpy.data.objects.new(f"PRACTICAL_{i}", d)
        o.location = (x, y, z)
        scene.collection.objects.link(o)
        put(o, "TH_PREVIEW_ONLY")
    return sun


# ------------------------------------------------------------------ actors
def place_actors(scene, cam, spec):
    """Protagonist + NPC stand-ins from the real 24x48 walker cells."""
    made = []
    for name, frame, y, height, x in spec["actors"]:
        ob = thestra_camera.create_actor_preview(
            str(WALKER), cam,
            anchor=(x, y, GROUND_Z),
            frame_width=24, frame_height=48, frame_index=frame,
            world_height=height, alpha_cutoff=0.5, name=name)
        # create_actor_preview orients the plane from the camera quaternion,
        # which for this calibration maps the plane's local +Y to world -Z.
        # The sprite therefore hangs DOWNWARD from its feet anchor, buried
        # under the street, and reads upside down. Set the basis explicitly:
        # local X -> +Y (screen right), local Y -> +Z (up), local Z -> +X.
        # Backface culling is off and the shader is emissive, so a normal
        # pointing away from the eye still renders, and the sprite is not
        # mirrored.
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Matrix(((0.0, 0.0, 1.0),
                                         (1.0, 0.0, 0.0),
                                         (0.0, 1.0, 0.0))).to_quaternion()
        put(ob, "TH_PREVIEW_ACTORS")
        made.append(ob)
    # create_actor_preview sets location/rotation but nothing flushes the
    # depsgraph, so matrix_world stays identity and the actors read as sitting
    # at the world origin -- which is behind this camera, hence invisible.
    bpy.context.view_layer.update()
    return made
