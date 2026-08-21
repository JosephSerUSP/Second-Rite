"""Clean-room scene scaffolding: empty reset, TH_* contract, UVs, lights, render.

Every attempt begins by calling `reset()`, which performs a hard
`bpy.ops.wm.read_factory_settings(use_empty=True)`. No .blend is ever opened
as a starting point, and no attempt module may import another attempt module.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

from . import camera as cr_camera

COLLECTIONS = (
    "TH_SOURCE",
    "TH_RENDER",
    "TH_COLLISION",
    "TH_ANCHORS",
    "TH_PREVIEW_ACTORS",
    "TH_PREVIEW_ONLY",
    "TH_CAMERA_PREVIEW",
)


class Stage:
    """Handle onto a freshly constructed, empty, calibrated scene."""

    def __init__(self, record, cam, solve, cols):
        self.record = record
        self.cam = cam
        self.solve = solve
        self.cols = cols
        self.plane_x = solve["planeX"]
        self.px_per_unit = float(cr_camera.ACTOR_FRAME_H) / cr_camera.ACTOR_WORLD_HEIGHT
        self.eye = Vector(solve["eye"])
        self.anchors = {}

    # -- collections ------------------------------------------------------
    @property
    def source(self):
        return self.cols["TH_SOURCE"]

    @property
    def render(self):
        return self.cols["TH_RENDER"]

    @property
    def collision(self):
        return self.cols["TH_COLLISION"]

    @property
    def preview(self):
        return self.cols["TH_PREVIEW_ONLY"]

    # -- framing helpers --------------------------------------------------
    def px_per_unit_at(self, x):
        """Vertical pixels per world unit for a plane at depth x."""
        return self.px_per_unit * (self.plane_x - self.eye.x) / (x - self.eye.x)

    def screen_span(self, x):
        """(y_min, y_max, z_min, z_max) visible at depth x."""
        s = self.px_per_unit_at(x)
        half_w = (426.0 * 0.5) / s
        top = float(self.record["viewportCenterY"]) / s
        bottom = (240.0 - float(self.record["viewportCenterY"])) / s
        return (self.eye.y - half_w, self.eye.y + half_w, -bottom, top)

    def project(self, point):
        import thestra_camera as tc
        return tc.project_world_point(bpy.context.scene, self.cam, point)

    # -- anchors ----------------------------------------------------------
    def anchor(self, name, location, *, kind="point", forward=(0, 1, 0)):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.4
        empty.location = Vector(location)
        empty["thestra_anchor_kind"] = kind
        self.cols["TH_ANCHORS"].objects.link(empty)
        self.anchors[name] = {"kind": kind, "location": list(location)}
        return empty


def reset():
    """Hard factory reset to a genuinely empty file. The clean-room guarantee."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.textures, bpy.data.node_groups, bpy.data.cameras,
                  bpy.data.lights, bpy.data.collections, bpy.data.objects):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:
                pass
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.device = "CPU"
    except Exception:
        pass
    return scene


def make_stage(*, offset_x=0.0):
    scene = bpy.context.scene
    cols = {}
    for name in COLLECTIONS:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
        cols[name] = col

    record = cr_camera.load(offset_x=offset_x)
    cam = cr_camera.make_camera(record, scene=scene, make_active=True)
    # move the camera object into its contract collection
    for col in list(cam.users_collection):
        col.objects.unlink(cam)
    cols["TH_CAMERA_PREVIEW"].objects.link(cam)

    solve = cr_camera.solve_action_plane(record, cam, scene=scene)
    return Stage(record, cam, solve, cols)


# --------------------------------------------------------------------------
# UV convention  (Phase 4: one shared world-scale mapping)
# --------------------------------------------------------------------------

def world_box_uv(obj, *, tile=1.0, offset=(0.0, 0.0)):
    """Box-project world coordinates into UV at a shared physical scale.

    A stone block keeps the same physical size whether it lands on a large
    wall, a narrow jamb or a foreground plinth, because UV is world position
    divided by a metre-valued tile size -- never a per-object 0..1 normalise.
    """
    mesh = obj.data
    if not mesh.polygons:
        return obj
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    mw = obj.matrix_world
    ou, ov = offset
    for poly in mesh.polygons:
        n = (mw.to_3x3() @ poly.normal).normalized()
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            w = mw @ mesh.vertices[vi].co
            if az >= ax and az >= ay:
                u, v = w.x, w.y
            elif ax >= ay:
                u, v = w.y, w.z
            else:
                u, v = w.x, w.z
            uv.data[li].uv = (u / tile + ou, v / tile + ov)
    mesh.update()
    return obj


def unwrap_atlas(obj, margin=0.02):
    """Non-overlapping atlas UVs for a bake *target*."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    uv = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")
    obj.data.uv_layers.active = uv
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def shade_smooth(obj, angle=math.radians(32)):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    try:
        mod = obj.modifiers.new("smooth_by_angle", "SMOOTH_BY_ANGLE")
        mod.angle = angle
    except Exception:
        try:
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = angle
        except Exception:
            pass
    return obj


# --------------------------------------------------------------------------
# lighting
# --------------------------------------------------------------------------

def sky(stage, *, top=(0.30, 0.40, 0.55), horizon=(0.55, 0.52, 0.46),
        strength=1.0):
    """Two-tone gradient world. Values are LINEAR, authored as linear."""
    world = bpy.data.worlds.new("TH_WORLD")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (*horizon, 1.0)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (*top, 1.0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


def sun(stage, *, energy=3.0, color=(1.0, 0.94, 0.84), direction=None,
        azimuth=35.0, elevation=42.0, size=0.09, name="TH_SUN"):
    """Directional light aimed by the direction light TRAVELS.

    Euler angles are a trap here. The camera looks along +X, so every
    camera-facing surface has normal -X and is lit only when the light travels
    with a POSITIVE X component. An azimuth/elevation pair makes that
    impossible to get wrong: azimuth 0 puts the sun directly behind the eye,
    positive azimuth swings it toward screen-right (+Y).
    """
    if direction is None:
        az = math.radians(azimuth)
        el = math.radians(elevation)
        direction = (math.cos(el) * math.cos(az),
                     math.cos(el) * math.sin(az),
                     -math.sin(el))
    d = Vector(direction)
    d.normalize()
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.color = color
    data.angle = size
    obj = bpy.data.objects.new(name, data)
    # a sun object emits along its local -Z
    obj.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    obj.location = Vector((0.0, 0.0, 0.0))
    stage.preview.objects.link(obj)
    obj["thestra_light_direction"] = tuple(d)
    return obj


def area(stage, *, location, energy=200.0, color=(1.0, 0.86, 0.66), size=2.0,
         rotation=(0, 0, 0), name="TH_FILL"):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.color = color
    data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = Vector(location)
    obj.rotation_euler = tuple(math.radians(a) for a in rotation)
    stage.preview.objects.link(obj)
    return obj


def point(stage, *, location, energy=40.0, color=(1.0, 0.72, 0.40),
          radius=0.12, name="TH_LAMP"):
    data = bpy.data.lights.new(name, type="POINT")
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    obj.location = Vector(location)
    stage.preview.objects.link(obj)
    return obj


# --------------------------------------------------------------------------
# actors  (walker.png only)
# --------------------------------------------------------------------------

def actor(stage, name, *, anchor, frame_index=0, world_height=None):
    """Stage a walker.png frame as a preview-only, camera-facing plane."""
    import thestra_camera as tc
    obj = tc.create_actor_preview(
        str(cr_camera.WALKER), stage.cam,
        anchor=anchor,
        frame_width=cr_camera.ACTOR_FRAME_W,
        frame_height=cr_camera.ACTOR_FRAME_H,
        frame_index=frame_index,
        world_height=world_height or cr_camera.ACTOR_WORLD_HEIGHT,
        name=name,
    )
    bpy.context.view_layer.update()
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    stage.cols["TH_PREVIEW_ACTORS"].objects.link(obj)
    bpy.context.view_layer.update()
    return obj


def walker_frame_count():
    import thestra_camera as tc
    info = tc.inspect_sprite_sheet(str(cr_camera.WALKER),
                                   cr_camera.ACTOR_FRAME_W,
                                   cr_camera.ACTOR_FRAME_H)
    return info


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def render(path, *, samples=96, film_transparent=False, view_transform="Filmic",
           exposure=0.0, look="None"):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.device = "CPU"
    except Exception:
        pass
    scene.cycles.samples = int(samples)
    scene.cycles.use_denoising = True
    scene.render.film_transparent = film_transparent
    scene.render.filter_size = 0.9
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = view_transform
        scene.view_settings.look = look
        scene.view_settings.exposure = exposure
    except Exception:
        pass
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def hide_render(collection, hidden=True):
    if collection is None:
        return
    collection.hide_render = hidden
    for obj in collection.objects:
        obj.hide_render = hidden


def save(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return path
