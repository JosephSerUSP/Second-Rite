"""Second Gate clean-room town visual gauntlet.

This file is intentionally self-contained.  It uses only generic Blender
primitives, the owner-selected Thestra camera calibration, and the one
pre-existing visual asset allowed by the brief: walker.png.

Every attempt calls read_factory_settings(use_empty=True) before authoring.
The nine builders are deliberately separate authored compositions; they share
only primitive/material/camera helpers, never scene data or coordinates.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "cleanroom_town_gauntlet"
ATTEMPTS = OUT / "attempts"
RUNTIME = OUT / "selected_runtime"
WALKER = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"

W = 426
H = 240
GROUND_Z = -1.5
ACTOR_X = 5.35
CAMERA_EYE = (-13.3175, 5.5, 0.0)

# This is the accepted Thestra calibration record from the playability seam.
# It is reproduced here as a downstream input, never authored back to the
# engine.  The helper below is a compact local adapter for this clean-room run.
CALIBRATION = {
    "contract": "thestra.world-camera-calibration",
    "version": 1,
    "projection": "perspective",
    "targetWidth": 426,
    "targetHeight": 240,
    "baseViewportWidth": 256,
    "baseViewportHeight": 144,
    "viewportCenterX": 213,
    "viewportCenterY": 110,
    "nearPlane": 0.05,
    "farPlane": 64.0,
    "fovHalfX": 0.25,
    "fovHalfY": 0.140625,
    "projectionScale": {"x": 1.0, "y": 1.0},
    "projectionWindowOffsetX": 0.0,
    "projectionWindowOffsetY": 0.0,
    "eye": {"x": CAMERA_EYE[0], "y": CAMERA_EYE[1], "z": CAMERA_EYE[2]},
    "orientation": {
        "forwardX": 1.0, "forwardY": 0.0, "rightX": 0.0, "rightY": 1.0,
        "pitchRadians": 0.0,
    },
    "townActorSolve": {
        "targetHeightPixels": 48.0,
        "actorWorldAnchor": [5.35, 5.5, -1.5],
        "actorWorldHeight": 1.75,
        "distance": 21.1175,
        "method": "runtime-lovec-calibration -> Blender world_to_camera_view binary search",
    },
}

COLLECTION_NAMES = [
    "TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS",
    "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW", "TH_LIGHTS",
]

MATS = {}
ACTOR_IMAGE = None
CAMERA = None
BASE_CAMERA_SHIFT = (0.0, 0.0)


def srgb(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def col(name: str):
    return bpy.data.collections[name]


def move_to(obj, collection_name: str):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col(collection_name).objects.link(obj)
    return obj


def reset_scene():
    global ACTOR_IMAGE
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ACTOR_IMAGE = None
    scene = bpy.context.scene
    # Blender 4.1 names the realtime engine BLENDER_EEVEE; newer releases
    # expose the same engine as BLENDER_EEVEE_NEXT.
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in {i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(OUT / "scratch.png")
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.image_settings.color_mode = "RGBA"
    for name in COLLECTION_NAMES:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
    setup_world(scene)
    make_materials()
    create_camera(scene)
    setup_lights(scene)
    return scene


def setup_world(scene):
    world = bpy.data.worlds.new("CleanroomSky")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (srgb(0.065), srgb(0.10), srgb(0.17), 1.0)
    bg.inputs["Strength"].default_value = 0.34
    scene.world = world


def make_material(name, base, roughness, *, metallic=0.0, pattern=4.0, accent=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = pattern
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    dark = tuple(srgb(max(0.0, c * 0.63)) for c in base) + (1.0,)
    light = tuple(srgb(min(1.0, c * 1.28 + 0.035)) for c in (accent or base)) + (1.0,)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[0].position = 0.26
    ramp.color_ramp.elements[1].color = light
    ramp.color_ramp.elements[1].position = 0.76
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18 if name not in {"M_Glass", "M_Cloth"} else 0.05
    bump.inputs["Distance"].default_value = 0.045
    mapping.inputs["Scale"].default_value = (0.82, 0.82, 0.82)
    nt.links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.3
    if name == "M_Glass" and "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.24
        bsdf.inputs["Coat Weight"].default_value = 0.45
    mat["cleanroom_provenance"] = "procedural material authored during this task"
    MATS[name] = mat
    return mat


def make_materials():
    MATS.clear()
    make_material("M_Stone", (0.28, 0.31, 0.34), 0.83, pattern=3.7, accent=(0.46, 0.49, 0.50))
    make_material("M_Plaster", (0.62, 0.49, 0.36), 0.92, pattern=2.2, accent=(0.80, 0.68, 0.51))
    make_material("M_Timber", (0.25, 0.10, 0.055), 0.82, pattern=5.6, accent=(0.50, 0.22, 0.09))
    make_material("M_Roof", (0.24, 0.07, 0.065), 0.76, pattern=8.0, accent=(0.57, 0.16, 0.10))
    make_material("M_Paving", (0.22, 0.24, 0.23), 0.96, pattern=11.0, accent=(0.44, 0.42, 0.35))
    make_material("M_Metal", (0.30, 0.25, 0.16), 0.38, metallic=0.76, pattern=7.5, accent=(0.72, 0.50, 0.20))
    make_material("M_Painted", (0.21, 0.34, 0.38), 0.75, pattern=3.0, accent=(0.58, 0.72, 0.67))
    make_material("M_Glass", (0.16, 0.34, 0.44), 0.22, metallic=0.08, pattern=1.5, accent=(0.45, 0.78, 0.86))
    make_material("M_Cloth", (0.55, 0.20, 0.17), 0.98, pattern=13.0, accent=(0.80, 0.42, 0.24))
    make_material("M_Grime", (0.12, 0.17, 0.10), 1.0, pattern=4.2, accent=(0.25, 0.32, 0.12))
    make_material("M_Ornament", (0.50, 0.17, 0.055), 0.55, metallic=0.35, pattern=5.0, accent=(0.93, 0.61, 0.18))
    make_material("M_Water", (0.04, 0.18, 0.24), 0.17, metallic=0.18, pattern=2.5, accent=(0.18, 0.57, 0.65))


def create_camera(scene):
    global CAMERA, BASE_CAMERA_SHIFT
    data = bpy.data.cameras.new("TH_CAMERA_PREVIEW")
    cam = bpy.data.objects.new("TH_CAMERA_PREVIEW", data)
    col("TH_CAMERA_PREVIEW").objects.link(cam)
    cam.location = Vector(CAMERA_EYE)
    # Camera local -Z points forward (+X), local +Y is world +Z, local +X is +Y.
    cam.matrix_world = Matrix(((0.0, 0.0, -1.0, CAMERA_EYE[0]),
                               (1.0, 0.0, 0.0, CAMERA_EYE[1]),
                               (0.0, 1.0, 0.0, CAMERA_EYE[2]),
                               (0.0, 0.0, 0.0, 1.0)))
    ax = CALIBRATION["projectionScale"]["x"] / CALIBRATION["fovHalfX"] * (256.0 / W)
    ay = CALIBRATION["projectionScale"]["y"] / CALIBRATION["fovHalfY"] * (144.0 / H)
    data.type = "PERSP"
    data.sensor_fit = "HORIZONTAL"
    data.sensor_width = 36.0
    data.lens = data.sensor_width * ax * 0.5
    data.clip_start = CALIBRATION["nearPlane"]
    data.clip_end = CALIBRATION["farPlane"]
    scene.render.pixel_aspect_x = (ay / ax) * (H / W)
    scene.render.pixel_aspect_y = 1.0
    scene.camera = cam
    # Principal point is calibrated through Blender's own projection helper.
    axis_point = cam.location + Vector((1.0, 0.0, 0.0)) * 1.0
    data.shift_x = 0.0
    data.shift_y = 0.0
    base = world_to_camera_view(scene, cam, axis_point)
    data.shift_x = 1.0
    probe_x = world_to_camera_view(scene, cam, axis_point)
    data.shift_x = (CALIBRATION["viewportCenterX"] / W - base.x) / (probe_x.x - base.x)
    data.shift_y = 0.0
    base_y = world_to_camera_view(scene, cam, axis_point)
    data.shift_y = 1.0
    probe_y = world_to_camera_view(scene, cam, axis_point)
    data.shift_y = (1.0 - CALIBRATION["viewportCenterY"] / H - base_y.y) / (probe_y.y - base_y.y)
    BASE_CAMERA_SHIFT = (data.shift_x, data.shift_y)
    cam["thestra_preview_only"] = True
    cam["calibration_contract"] = CALIBRATION["contract"]
    cam["calibration_fov_half_x"] = CALIBRATION["fovHalfX"]
    cam["calibration_pitch_degrees"] = 0.0
    cam["calibration_actor_height_px_target"] = 48.0
    CAMERA = cam
    return cam


def setup_lights(scene):
    sun_data = bpy.data.lights.new("CleanroomSun", "SUN")
    sun_data.energy = 1.65
    sun_data.angle = math.radians(16.0)
    sun_data.color = (1.0, 0.73, 0.51)
    sun = bpy.data.objects.new("CleanroomSun", sun_data)
    sun.rotation_euler = (math.radians(60), math.radians(-18), math.radians(-35))
    col("TH_LIGHTS").objects.link(sun)
    for i, (y, z, energy, color) in enumerate([
        (3.1, 0.0, 140.0, (1.0, 0.42, 0.18)),
        (7.8, 0.6, 95.0, (0.18, 0.45, 1.0)),
    ]):
        d = bpy.data.lights.new(f"Practical_{i}", "AREA")
        d.energy = energy
        d.color = color
        d.shape = "DISK"
        d.size = 1.1
        o = bpy.data.objects.new(f"Practical_{i}", d)
        o.location = (3.6, y, z)
        o.rotation_euler = (math.radians(90), 0.0, 0.0)
        col("TH_LIGHTS").objects.link(o)


def mesh_obj(name, verts, faces, collection, material=None):
    me = bpy.data.meshes.new(name + "_Mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    col(collection).objects.link(ob)
    if material:
        me.materials.append(material if isinstance(material, bpy.types.Material) else MATS[material])
    return ob


def box(name, x, y, z, sx, sy, sz, collection="TH_SOURCE", material="M_Stone", bevel=0.0):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    v = [(x-hx,y-hy,z-hz),(x+hx,y-hy,z-hz),(x+hx,y+hy,z-hz),(x-hx,y+hy,z-hz),
         (x-hx,y-hy,z+hz),(x+hx,y-hy,z+hz),(x+hx,y+hy,z+hz),(x-hx,y+hy,z+hz)]
    f = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    ob = mesh_obj(name, v, f, collection, material)
    if bevel:
        mod = ob.modifiers.new("soft authored edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return ob


def cylinder_x(name, x, y, z, radius, depth, collection="TH_SOURCE", material="M_Metal", segments=20):
    verts = []
    for side in (-1, 1):
        for i in range(segments):
            a = (i / segments) * math.tau
            verts.append((x + side * depth / 2, y + math.cos(a) * radius, z + math.sin(a) * radius))
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(segments, segments * 2)))
    return mesh_obj(name, verts, faces, collection, material)


def arch_ring(name, x, yc, zc, outer_w, outer_h, inner_w, inner_h, depth, material="M_Ornament", segments=18):
    # Semicircular upper ring. Door jambs are authored separately where needed.
    verts = []
    for side in (-1, 1):
        for inner in (False, True):
            w, h = (inner_w, inner_h) if inner else (outer_w, outer_h)
            for i in range(segments + 1):
                a = math.pi - (math.pi * i / segments)
                verts.append((x + side * depth / 2, yc + math.cos(a) * w / 2, zc + math.sin(a) * h / 2))
    faces = []
    stride = segments + 1
    # front/back strips between outer and inner curves
    for side_base in (0, 2 * stride):
        for i in range(segments):
            a = side_base + i
            b = side_base + i + 1
            c = side_base + stride + i + 1
            d = side_base + stride + i
            faces.append((a, b, c, d))
    # depth walls of the ring
    for i in range(segments):
        a, b = i, i + 1
        c, d = 2 * stride + i + 1, 2 * stride + i
        faces.append((a, c, d, a))
        a, b = stride + i, stride + i + 1
        c, d = 3 * stride + i + 1, 3 * stride + i
        faces.append((a, b, c, d))
    return mesh_obj(name, verts, faces, "TH_SOURCE", material)


def facade_panel(name, x, y0, z0, width, height, depth, material, seed, divisions=18, aggressive=False):
    """Dense real displaced source panel; never exported to runtime."""
    verts = []
    for j in range(divisions + 1):
        for i in range(divisions + 1):
            u = i / divisions
            v = j / divisions
            relief = (0.045 * math.sin((u * 8.0 + seed) * math.tau) * math.sin((v * 5.0 + seed * 0.17) * math.pi)
                      + 0.025 * math.sin((u * 17.0 - v * 11.0 + seed) * math.tau))
            if aggressive:
                relief += 0.035 * max(0.0, math.sin((u * 3.0 + v * 2.0 + seed) * math.tau))
            verts.append((x + relief, y0 + u * width, z0 + v * height))
    faces = []
    for j in range(divisions):
        for i in range(divisions):
            a = j * (divisions + 1) + i
            faces.append((a, a + divisions + 1, a + divisions + 2, a + 1))
    return mesh_obj(name, verts, faces, "TH_SOURCE", material)


def roof_slope(name, x, y, z, width, run, rise, material="M_Roof"):
    # Side-view wedge, with an intentionally non-symmetric eave.
    v = [(x-0.5,y-width/2,z),(x+0.5,y-width/2,z),(x-0.5,y+width/2,z),(x+0.5,y+width/2,z),
         (x-0.5,y-width/2+run,z+rise),(x+0.5,y-width/2+run,z+rise),
         (x-0.5,y+width/2+run*0.35,z+rise*0.72),(x+0.5,y+width/2+run*0.35,z+rise*0.72)]
    f = [(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5),(4,5,7,6),(0,2,3,1)]
    return mesh_obj(name, v, f, "TH_SOURCE", material)


def plank_screen(name, x, y, z, w, h, material="M_Timber", tilt=0.0):
    ob = box(name, x, y, z, 0.24, w, h, "TH_SOURCE", material, bevel=0.035)
    ob.rotation_euler[1] = tilt
    return ob


def empty_anchor(name, x, y, z=GROUND_Z, kind="point"):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = "PLAIN_AXES"
    ob.empty_display_size = 0.18
    ob.location = (x, y, z)
    ob["anchor_id"] = name
    ob["kind"] = kind
    col("TH_ANCHORS").objects.link(ob)
    return ob


def common_floor(scene_name, paving="M_Paving"):
    # The camera's native window is wider than the first pass's 9.4-unit
    # staging strip. A continuous floor shell keeps the side-view composition
    # a place rather than a floating diorama with black side gutters.
    box(scene_name + "_street_runtime", 6.8, 5.5, -1.66, 4.2, 15.5, 0.28, "TH_RENDER", paving)
    box(scene_name + "_street_source", 6.8, 5.5, -1.66, 4.2, 15.5, 0.28, "TH_SOURCE", paving, bevel=0.06)
    # A side-view room needs a visible near-side floor plane below the feet;
    # a level ground slab alone is edge-on at zero pitch and leaves the lower
    # third of the native frame empty.
    box(scene_name + "_street_drop", 6.1, 5.5, -4.0, 1.35, 15.5, 5.0, "TH_SOURCE", paving, bevel=0.05)
    box(scene_name + "_street_drop_runtime", 6.1, 5.5, -4.0, 1.35, 15.5, 5.0, "TH_RENDER", paving)
    for i, y in enumerate([0.3, 1.15, 2.0, 2.85, 3.7, 4.55, 5.4, 6.25, 7.1, 7.95, 8.8, 9.65, 10.5]):
        box(scene_name + "_paving_%02d" % i, 5.0, y, -1.48, 0.22, 0.62, 0.06, "TH_SOURCE", "M_Paving")


def common_anchors(door_y, npc_ys, fg_y, bounds=(1.45, 9.55)):
    empty_anchor("spawn_player", ACTOR_X, 4.0, kind="spawn")
    empty_anchor("door_threshold", ACTOR_X, door_y, kind="door")
    empty_anchor("npc_01", ACTOR_X, npc_ys[0], kind="npc")
    empty_anchor("npc_02", ACTOR_X, npc_ys[1], kind="npc")
    if len(npc_ys) > 2:
        empty_anchor("npc_03", ACTOR_X, npc_ys[2], kind="npc")
    empty_anchor("foreground_occluder", 4.0, fg_y, -0.7, kind="occluder")
    empty_anchor("environment_min", ACTOR_X, bounds[0], kind="bounds")
    empty_anchor("environment_max", ACTOR_X, bounds[1], kind="bounds")
    collision = box("walk_space", 6.2, (bounds[0] + bounds[1]) / 2, -1.68, 3.0, bounds[1] - bounds[0], 0.32, "TH_COLLISION", None)
    collision["collision_kind"] = "horizontal_walk_space"
    empty_anchor("walk_route_start", ACTOR_X, bounds[0], kind="walk-bound")
    empty_anchor("walk_route_end", ACTOR_X, bounds[1], kind="walk-bound")


def create_actor(name, frame, y, x=4.55, height=1.75):
    global ACTOR_IMAGE
    if ACTOR_IMAGE is None:
        ACTOR_IMAGE = bpy.data.images.load(str(WALKER.resolve()), check_existing=True)
    mesh = bpy.data.meshes.new(name + "_Mesh")
    w = height * 24.0 / 48.0
    mesh.from_pydata([(-w/2,0,0),(w/2,0,0),(w/2,height,0),(-w/2,height,0)], [], [(0,1,2,3)])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    u0, u1 = frame / 6.0, (frame + 1) / 6.0
    # The source sheet is top-origin while the Blender plane is bottom-origin.
    # Mapping the plane's bottom edge to v=1 keeps the Walker upright.
    coords = [(u0,1.0),(u1,1.0),(u1,0.0),(u0,0.0)]
    for loop in mesh.loops:
        uv.data[loop.index].uv = coords[loop.vertex_index]
    mat = bpy.data.materials.get("WalkerCleanroom")
    if mat is None:
        mat = bpy.data.materials.new("WalkerCleanroom")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = ACTOR_IMAGE
        tex.interpolation = "Closest"
        tex.extension = "CLIP"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        less = nt.nodes.new("ShaderNodeMath")
        less.operation = "LESS_THAN"
        less.inputs[1].default_value = 0.34
        nt.links.new(tex.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Blue"], sub.inputs[0])
        nt.links.new(sep.outputs["Red"], sub.inputs[1])
        nt.links.new(sub.outputs[0], less.inputs[0])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(less.outputs[0], bsdf.inputs["Alpha"])
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 1.0
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.0
        if "Emission Color" in bsdf.inputs:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 0.35
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
        # Alpha is explicit on Principled; this survives Eevee's material
        # surface handling more reliably than a transparent-mix fallback.
        mat.blend_method = "HASHED"
        mat.surface_render_method = "DITHERED"
        mat["cleanroom_provenance"] = "walker.png only pre-existing visual input"
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    col("TH_PREVIEW_ACTORS").objects.link(ob)
    ob.location = (x, y, GROUND_Z)
    ob.rotation_mode = "QUATERNION"
    # The Blender camera basis is a projection basis with a reflected screen
    # convention; using its quaternion directly flips a billboard vertically.
    # Use the proper right-handed actor basis explicitly: local X -> world +Y,
    # local Y -> world +Z, local Z -> world +X.
    ob.rotation_quaternion = Matrix(((0.0, 0.0, 1.0),
                                     (1.0, 0.0, 0.0),
                                     (0.0, 1.0, 0.0))).to_quaternion()
    ob["frame_index"] = frame
    ob["feet_anchor"] = True
    return ob


def actors(npc_ys):
    create_actor("ACTOR_protagonist", 0, 4.15)
    for i, y in enumerate(npc_ys):
        create_actor("ACTOR_npc_%02d" % (i + 1), i + 1, y, height=1.63 + i * 0.035)


def backdrop(name, x=9.4, z=2.0, mat="M_Plaster"):
    # Full-width room shell: the authored façades sit in front of this wall,
    # so every native pixel belongs to a spatial envelope even where the
    # composition intentionally quiets down.
    box(name + "_room_shell", x, 5.5, z, 0.18, 15.5, 8.6, "TH_SOURCE", mat)
    box(name + "_room_lintel", x - 2.0, 5.5, 5.95, 0.55, 15.5, 0.42, "TH_SOURCE", "M_Timber", bevel=0.05)


# The nine functions below are intentionally independent authored compositions.
def build_01():
    common_floor("bellwater_fold")
    backdrop("bellwater_fold")
    box("fold_left_mass", 7.8, 2.55, 1.25, 2.4, 2.5, 5.4, "TH_SOURCE", "M_Plaster", bevel=0.1)
    box("fold_right_mass", 7.4, 7.6, 1.0, 2.9, 2.7, 4.9, "TH_SOURCE", "M_Stone", bevel=0.1)
    box("fold_tower", 7.1, 5.7, 2.55, 2.4, 1.55, 8.3, "TH_SOURCE", "M_Stone", bevel=0.12)
    facade_panel("fold_tower_relief", 5.88, 4.92, -1.5, 1.55, 8.1, 0.05, "M_Stone", 1.4, divisions=20)
    arch_ring("fold_bell_arch", 5.65, 5.7, 3.35, 1.18, 2.0, 0.72, 1.42, 0.25, "M_Ornament")
    box("fold_door_recess", 5.58, 3.95, -0.35, 0.7, 1.12, 2.3, "TH_SOURCE", "M_Grime")
    box("fold_door_trim_l", 5.36, 3.36, -0.25, 0.28, 0.18, 2.5, "TH_SOURCE", "M_Timber")
    box("fold_door_trim_r", 5.36, 4.54, -0.25, 0.28, 0.18, 2.5, "TH_SOURCE", "M_Timber")
    roof_slope("fold_left_roof", 5.85, 2.6, 4.2, 2.75, 1.0, 1.0)
    roof_slope("fold_right_roof", 5.8, 7.7, 3.7, 2.9, -0.8, 0.9, "M_Roof")
    plank_screen("fold_foreground_screen", 3.85, 2.15, 0.9, 1.15, 4.0, "M_Timber", tilt=-0.06)
    cylinder_x("fold_bell", 5.45, 5.7, 6.35, 0.33, 0.65, "TH_SOURCE", "M_Metal", 24)
    common_anchors(3.95, [5.2, 7.15], 2.15)
    actors([5.2, 7.15])
    return "Bellwater Fold", "A stepped civic fold with a narrow bell mass and diagonal foreground screen."


def build_02():
    common_floor("lantern_court", "M_Paving")
    backdrop("lantern_court", x=9.2, mat="M_Plaster")
    box("court_low_left", 7.6, 2.25, 0.35, 2.6, 2.25, 3.7, "TH_SOURCE", "M_Plaster", bevel=0.08)
    box("court_low_right", 7.25, 8.05, 0.3, 3.0, 2.35, 3.6, "TH_SOURCE", "M_Painted", bevel=0.08)
    box("court_courtwall", 7.0, 5.35, 1.2, 2.8, 1.15, 5.2, "TH_SOURCE", "M_Stone")
    facade_panel("court_wall_skin", 5.57, 4.78, -1.5, 1.15, 5.25, 0.05, "M_Plaster", 2.7, divisions=17)
    box("court_offset_door", 5.38, 6.85, -0.25, 0.72, 1.0, 2.5, "TH_SOURCE", "M_Grime")
    box("court_offset_door_top", 5.18, 6.85, 1.16, 0.34, 1.45, 0.22, "TH_SOURCE", "M_Timber")
    roof_slope("court_left_canopy", 5.7, 2.25, 2.85, 2.3, 0.85, 0.65, "M_Roof")
    roof_slope("court_right_canopy", 5.6, 8.05, 2.8, 2.45, 0.6, 0.7, "M_Cloth")
    for i, y in enumerate([2.05, 2.55, 8.1, 8.6]):
        plank_screen("court_lantern_post_%d" % i, 4.75, y, 0.05, 0.18, 2.6, "M_Timber")
        cylinder_x("court_lantern_%d" % i, 4.48, y, 1.3, 0.16, 0.24, "TH_SOURCE", "M_Metal", 12)
    box("court_foreground_sill", 3.95, 7.8, -0.2, 0.5, 2.0, 1.65, "TH_SOURCE", "M_Timber", bevel=0.08)
    common_anchors(6.85, [4.0, 8.55], 7.8)
    actors([4.0, 8.55])
    return "Lantern Court", "A compressed court that leaves a deliberate quiet gap around an offset threshold."


def build_03():
    common_floor("silt_crown_arcade")
    backdrop("silt_crown_arcade", x=9.6, mat="M_Grime")
    box("arcade_back_mass", 7.65, 5.5, 1.5, 3.2, 8.3, 6.2, "TH_SOURCE", "M_Stone", bevel=0.07)
    facade_panel("arcade_displaced_wall", 5.98, 1.45, -1.5, 8.1, 6.0, 0.06, "M_Stone", 3.8, divisions=32, aggressive=True)
    # Five deliberately unequal bay cuts expressed as deep, author-specific recesses.
    for i, (y, z, h) in enumerate([(2.05, 0.3, 3.1), (3.55, 0.0, 4.6), (5.0, 0.25, 3.5), (6.5, 0.0, 5.0), (8.25, 0.2, 3.7)]):
        box("arcade_recess_%d" % i, 5.38, y, z, 0.72, 0.82, h, "TH_SOURCE", "M_Grime")
        box("arcade_jamb_%d" % i, 5.15, y - 0.56, z + 0.7, 0.32, 0.16, h + 0.6, "TH_SOURCE", "M_Timber")
        box("arcade_jamb_r_%d" % i, 5.15, y + 0.56, z + 0.7, 0.32, 0.16, h + 0.6, "TH_SOURCE", "M_Timber")
    arch_ring("arcade_waydoor", 5.04, 3.55, 2.0, 1.3, 2.2, 0.82, 1.62, 0.28, "M_Ornament")
    for y in [2.0, 4.8, 7.95]:
        box("arcade_ledger_%0.1f" % y, 5.0, y, 4.95, 0.24, 1.1, 0.22, "TH_SOURCE", "M_Timber")
    plank_screen("arcade_foreground_lattice", 3.7, 8.45, 0.1, 0.7, 3.2, "M_Timber", tilt=0.12)
    common_anchors(3.55, [2.25, 6.65, 8.65], 8.45)
    actors([2.25, 6.65, 8.65])
    return "Silt-Crown Arcade", "A long irregular arcade where costly displaced relief carries the skyline and the route."


def build_04():
    common_floor("needle_forum")
    backdrop("needle_forum", x=9.8, mat="M_Plaster")
    box("forum_low_wing", 7.6, 2.5, 0.65, 3.0, 2.5, 4.3, "TH_SOURCE", "M_Plaster", bevel=0.1)
    box("forum_needle_tower", 7.0, 7.15, 2.1, 3.4, 2.25, 7.4, "TH_SOURCE", "M_Stone", bevel=0.12)
    facade_panel("forum_needle_skin", 5.28, 6.05, -1.5, 2.2, 7.0, 0.07, "M_Stone", 5.2, divisions=38, aggressive=True)
    # Tower cap and a thin needle create the one aggressive high/low read.
    box("forum_cap", 5.1, 7.2, 5.85, 0.5, 2.8, 0.25, "TH_SOURCE", "M_Ornament")
    box("forum_needle", 5.02, 7.2, 7.25, 0.38, 0.22, 2.6, "TH_SOURCE", "M_Metal", bevel=0.05)
    arch_ring("forum_main_arch", 5.0, 7.15, 2.15, 1.7, 3.25, 1.02, 2.48, 0.32, "M_Ornament", segments=26)
    box("forum_door_void", 4.78, 7.15, -0.15, 0.42, 1.0, 2.6, "TH_SOURCE", "M_Grime")
    box("forum_quiet_wall", 5.08, 4.7, 1.0, 0.45, 1.0, 5.6, "TH_SOURCE", "M_Plaster")
    box("forum_tower_plinth", 4.82, 7.15, -1.12, 0.72, 2.85, 0.52, "TH_SOURCE", "M_Stone", bevel=0.06)
    box("forum_clerestory_left", 5.35, 5.1, 4.7, 0.58, 1.55, 0.72, "TH_SOURCE", "M_Stone", bevel=0.06)
    box("forum_clerestory_right", 5.35, 8.65, 4.7, 0.58, 1.15, 0.72, "TH_SOURCE", "M_Stone", bevel=0.06)
    roof_slope("forum_high_eave", 5.42, 7.05, 5.56, 2.9, 0.95, 0.78, "M_Roof")
    for i, (y, z) in enumerate([(3.9, 2.2), (4.65, 3.15), (8.55, 2.6)]):
        box("forum_window_recess_%d" % i, 4.86, y, z, 0.22, 0.46, 0.72, "TH_SOURCE", "M_Glass")
        box("forum_window_head_%d" % i, 4.7, y, z + 0.48, 0.25, 0.62, 0.12, "TH_SOURCE", "M_Timber")
    for i, (y, z, sy) in enumerate([(6.45, -1.26, 1.55), (6.65, -1.02, 1.15), (6.85, -0.78, 0.78)]):
        box("forum_threshold_step_%d" % i, 4.35, y, z, 0.48, sy, 0.22, "TH_SOURCE", "M_Stone", bevel=0.035)
    plank_screen("forum_foreground_frame", 3.45, 2.15, 1.0, 0.42, 4.8, "M_Timber", tilt=-0.11)
    cylinder_x("forum_rune_disc", 4.65, 4.72, 1.85, 0.56, 0.22, "TH_SOURCE", "M_Metal", 28)
    common_anchors(7.15, [3.0, 8.0], 2.15)
    actors([3.0, 8.0])
    return "Needle Forum", "A high, quiet civic needle with one deep arch and an unusually forceful vertical silhouette."


def build_05():
    common_floor("windglass_row")
    backdrop("windglass_row", x=9.1, mat="M_Painted")
    box("row_house_a", 7.65, 2.55, 0.45, 2.9, 2.2, 4.1, "TH_SOURCE", "M_Plaster", bevel=0.07)
    box("row_house_b", 7.35, 5.15, 0.8, 2.6, 2.15, 4.8, "TH_SOURCE", "M_Painted", bevel=0.07)
    box("row_house_c", 7.9, 7.9, 0.35, 2.5, 2.2, 3.9, "TH_SOURCE", "M_Plaster", bevel=0.07)
    facade_panel("row_house_b_skin", 6.02, 4.08, -1.5, 2.1, 4.65, 0.05, "M_Painted", 7.4, divisions=22)
    box("row_door", 5.42, 4.65, -0.2, 0.65, 0.9, 2.4, "TH_SOURCE", "M_Grime")
    box("row_door_frame", 5.18, 4.65, -0.1, 0.22, 1.18, 2.7, "TH_SOURCE", "M_Timber")
    for i, (y, z, mat) in enumerate([(2.55, 1.5, "M_Glass"), (5.3, 1.95, "M_Glass"), (7.9, 1.25, "M_Glass")]):
        box("row_window_%d" % i, 5.25, y, z, 0.18, 0.65, 0.85, "TH_SOURCE", mat)
    roof_slope("row_eave_a", 5.95, 2.55, 3.35, 2.15, 0.72, 0.56, "M_Roof")
    roof_slope("row_eave_b", 5.8, 5.15, 4.15, 2.2, -0.65, 0.8, "M_Roof")
    roof_slope("row_eave_c", 6.0, 7.9, 3.25, 2.2, 0.55, 0.52, "M_Roof")
    for i, y in enumerate([3.25, 6.15]):
        box("row_hanging_cloth_%d" % i, 4.6, y, 1.35, 0.12, 1.1, 1.8, "TH_SOURCE", "M_Cloth")
    box("row_foreground_ledge", 3.65, 8.75, -0.5, 0.7, 1.05, 2.2, "TH_SOURCE", "M_Timber", bevel=0.08)
    common_anchors(4.65, [3.2, 7.15], 8.75)
    actors([3.2, 7.15])
    return "Windglass Row", "A domestic row staggered by roof pitch, colored glass, and two hanging quiet cloth planes."


def build_06():
    common_floor("rain_cistern_crescent")
    backdrop("rain_cistern_crescent", x=9.5, mat="M_Grime")
    box("crescent_left", 7.8, 2.25, 0.55, 3.0, 2.1, 4.4, "TH_SOURCE", "M_Stone", bevel=0.08)
    box("crescent_right", 7.6, 8.35, 0.7, 3.0, 2.3, 4.7, "TH_SOURCE", "M_Plaster", bevel=0.08)
    facade_panel("crescent_left_skin", 6.12, 1.35, -1.5, 1.85, 5.1, 0.05, "M_Stone", 8.8, divisions=24)
    facade_panel("crescent_right_skin", 6.02, 7.3, -1.5, 1.95, 5.45, 0.05, "M_Plaster", 10.2, divisions=25)
    cylinder_x("crescent_cistern", 5.15, 5.75, -0.25, 1.55, 0.78, "TH_SOURCE", "M_Stone", 32)
    cylinder_x("crescent_water", 4.68, 5.75, -0.22, 1.15, 0.18, "TH_SOURCE", "M_Water", 32)
    for i, y in enumerate([4.1, 4.8, 6.7, 7.4]):
        box("crescent_cistern_rib_%d" % i, 4.62, y, -0.2, 0.18, 0.14, 2.6, "TH_SOURCE", "M_Metal")
    arch_ring("crescent_door_arch", 5.18, 7.6, 1.55, 1.3, 2.4, 0.8, 1.75, 0.3, "M_Timber")
    box("crescent_door", 4.98, 7.6, -0.15, 0.42, 0.78, 2.6, "TH_SOURCE", "M_Grime")
    plank_screen("crescent_foreground_bridge", 3.72, 4.0, 0.2, 2.3, 1.15, "M_Timber", tilt=0.2)
    common_anchors(7.6, [3.0, 8.45], 4.0)
    actors([3.0, 8.45])
    return "Rain-Cistern Crescent", "An open walking lane organized around a single wet, round civic object rather than a wall row."


def build_07():
    common_floor("mosaic_threshold")
    backdrop("mosaic_threshold", x=9.7, mat="M_Grime")
    box("mosaic_quiet_mass", 7.7, 2.75, 1.1, 3.2, 2.6, 5.4, "TH_SOURCE", "M_Plaster", bevel=0.12)
    box("mosaic_high_mass", 7.1, 7.75, 1.55, 3.0, 2.35, 6.3, "TH_SOURCE", "M_Stone", bevel=0.1)
    facade_panel("mosaic_high_relief", 5.52, 6.7, -1.5, 1.95, 6.2, 0.06, "M_Stone", 12.3, divisions=30, aggressive=True)
    box("mosaic_deep_recess", 5.05, 6.45, 0.2, 0.9, 1.28, 3.5, "TH_SOURCE", "M_Grime")
    box("mosaic_recess_left", 4.84, 5.75, 0.6, 0.38, 0.2, 4.35, "TH_SOURCE", "M_Ornament")
    box("mosaic_recess_right", 4.84, 7.15, 0.6, 0.38, 0.2, 4.35, "TH_SOURCE", "M_Ornament")
    arch_ring("mosaic_door_crown", 4.8, 6.45, 2.45, 1.45, 2.4, 0.9, 1.72, 0.34, "M_Ornament", 24)
    box("mosaic_offset_door", 4.65, 6.45, -0.25, 0.5, 0.9, 2.55, "TH_SOURCE", "M_Timber")
    box("mosaic_quiet_panel", 5.1, 4.35, 0.6, 0.35, 1.4, 3.6, "TH_SOURCE", "M_Plaster")
    plank_screen("mosaic_foreground_low_frame", 3.55, 8.2, -0.4, 1.25, 2.0, "M_Timber", tilt=-0.08)
    common_anchors(6.45, [4.2, 8.35], 8.2)
    actors([4.2, 8.35])
    return "Mosaic Threshold", "A new convergence reading built from a deep vertical recess, a quiet wall, and a shifted doorway."


def build_08():
    common_floor("brass_veil_passage")
    backdrop("brass_veil_passage", x=9.35, mat="M_Plaster")
    box("veil_low_left", 7.75, 2.2, 0.8, 3.0, 2.0, 4.9, "TH_SOURCE", "M_Stone", bevel=0.08)
    box("veil_civic_mass", 7.0, 6.95, 2.0, 3.5, 2.65, 7.1, "TH_SOURCE", "M_Stone", bevel=0.12)
    facade_panel("veil_civic_skin", 5.26, 5.72, -1.5, 2.5, 6.75, 0.07, "M_Stone", 14.9, divisions=42, aggressive=True)
    box("veil_cutout", 4.95, 6.75, 1.25, 0.62, 1.45, 4.85, "TH_SOURCE", "M_Grime")
    # The veil is a distinct vertical rhythm, not a reused arch recipe.
    for i in range(7):
        y = 6.05 + i * 0.24
        box("veil_brass_ribbon_%d" % i, 4.55, y, 1.3 + 0.13 * math.sin(i), 0.18, 0.09, 3.55, "TH_SOURCE", "M_Metal", bevel=0.025)
    box("veil_threshold", 4.65, 6.75, -0.15, 0.5, 1.0, 2.55, "TH_SOURCE", "M_Painted")
    roof_slope("veil_left_eave", 5.8, 2.2, 4.15, 2.0, 0.65, 0.66, "M_Roof")
    roof_slope("veil_civic_cap", 5.25, 6.95, 5.8, 2.75, -0.55, 0.85, "M_Roof")
    arch_ring("veil_foreground_arc", 3.65, 3.25, 1.7, 1.5, 3.6, 0.95, 2.85, 0.32, "M_Ornament", 22)
    common_anchors(6.75, [3.0, 8.25], 3.25)
    actors([3.0, 8.25])
    return "Brass Veil Passage", "A fresh civic passage whose memorable decision is a hanging vertical brass veil inside a cutout."


def build_09():
    common_floor("red_eave_house")
    backdrop("red_eave_house", x=9.4, mat="M_Painted")
    box("eave_house_left", 7.7, 2.65, 0.75, 3.2, 2.55, 4.8, "TH_SOURCE", "M_Plaster", bevel=0.08)
    box("eave_house_center", 7.3, 5.55, 1.0, 3.1, 2.1, 5.4, "TH_SOURCE", "M_Painted", bevel=0.1)
    box("eave_house_right", 7.8, 8.1, 0.45, 2.65, 2.0, 4.0, "TH_SOURCE", "M_Stone", bevel=0.08)
    facade_panel("eave_center_skin", 5.7, 4.45, -1.5, 1.95, 5.2, 0.05, "M_Painted", 17.1, divisions=28)
    facade_panel("eave_left_relief", 5.92, 1.45, -1.5, 2.0, 4.8, 0.05, "M_Plaster", 18.4, divisions=24)
    roof_slope("eave_giant_red", 5.25, 4.15, 4.45, 3.25, 1.45, 0.95, "M_Roof")
    box("eave_brace_left", 4.92, 4.0, 1.3, 0.32, 0.18, 3.8, "TH_SOURCE", "M_Timber")
    box("eave_brace_right", 4.92, 5.0, 1.3, 0.32, 0.18, 3.8, "TH_SOURCE", "M_Timber")
    box("eave_door_void", 4.85, 6.35, -0.2, 0.62, 0.9, 2.5, "TH_SOURCE", "M_Grime")
    cylinder_x("eave_round_window", 4.7, 3.0, 1.45, 0.52, 0.2, "TH_SOURCE", "M_Glass", 24)
    for i, y in enumerate([2.2, 8.1]):
        box("eave_sign_%d" % i, 4.65, y, 1.35, 0.16, 0.82, 0.42, "TH_SOURCE", "M_Ornament", bevel=0.04)
    plank_screen("eave_foreground_cart", 3.5, 7.9, -0.25, 1.45, 2.2, "M_Timber", tilt=0.15)
    common_anchors(6.35, [3.45, 8.65], 7.9)
    actors([3.45, 8.65])
    return "House of the Red Eave", "A domestic landmark defined by a sloping red canopy, a round window, and an offset door."


BUILDERS = {
    "01": build_01, "02": build_02, "03": build_03, "04": build_04, "05": build_05,
    "06": build_06, "07": build_07, "08": build_08, "09": build_09,
}


def tri_count(collection_name):
    return sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
               for o in col(collection_name).objects if o.type == "MESH")


def add_runtime_occluder(name, y, z, sy, sz, mat="M_Timber"):
    return box(name, 3.7, y, z, 0.5, sy, sz, "TH_RENDER", mat)


def render(path: Path):
    scene = bpy.context.scene
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def configure_source_render():
    col("TH_SOURCE").hide_render = False
    col("TH_RENDER").hide_render = True
    col("TH_PREVIEW_ACTORS").hide_render = False
    col("TH_PREVIEW_ONLY").hide_render = True


def author_runtime_shape(attempt_id: str):
    # The runtime representation intentionally stays coarse. The front plane
    # is inserted later after the winner's camera-space beauty bake is made.
    add_runtime_occluder("runtime_foreground_occluder", {
        "01":2.15,"02":7.8,"03":8.45,"04":2.15,"05":8.75,"06":4.0,
        "07":8.2,"08":3.25,"09":7.9,
    }[attempt_id], -0.05, 1.95, 2.0, "M_Timber")
    # A separate coarse skyline gives the package depth even before the atlas plane.
    box("runtime_depth_mass", 7.0, 5.5, 1.1, 3.0, 8.5, 5.3, "TH_RENDER", "M_Grime")


def project_actor_measurement():
    feet = world_to_camera_view(bpy.context.scene, CAMERA, Vector((ACTOR_X, 5.5, GROUND_Z)))
    top = world_to_camera_view(bpy.context.scene, CAMERA, Vector((ACTOR_X, 5.5, GROUND_Z + 1.75)))
    return abs((1.0 - top.y) * H - (1.0 - feet.y) * H)


def save_blend(path: Path):
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def run_material_test():
    scene = reset_scene()
    col("TH_SOURCE").hide_render = False
    col("TH_RENDER").hide_render = True
    for i, name in enumerate(["M_Stone","M_Plaster","M_Timber","M_Roof","M_Paving","M_Metal","M_Painted","M_Glass","M_Cloth","M_Ornament","M_Grime","M_Water"]):
        x = 4.8
        y = 1.4 + (i % 6) * 1.45
        z = -0.8 + (i // 6) * 1.65
        box("mat_test_%02d" % i, x, y, z, 0.35, 1.1, 1.1, "TH_SOURCE", name, bevel=0.06)
    render(OUT / "material_test.png")
    save_blend(OUT / "material_test.blend")


def run_attempt(attempt_id: str):
    scene = reset_scene()
    title, concept = BUILDERS[attempt_id]()
    source_triangles = tri_count("TH_SOURCE")
    render_triangles_before = tri_count("TH_RENDER")
    configure_source_render()
    native = ATTEMPTS / ("attempt_%s.png" % attempt_id)
    render(native)
    author_runtime_shape(attempt_id)
    render_triangles = tri_count("TH_RENDER")
    save_blend(ATTEMPTS / ("attempt_%s_source.blend" % attempt_id))
    record = {
        "id": attempt_id,
        "title": title,
        "concept": concept,
        "sourceTris": source_triangles,
        "renderTris": render_triangles,
        "reductionRatio": (source_triangles / max(1, render_triangles)),
        "actorHeightPx": project_actor_measurement(),
        "camera": {
            "output": [W, H], "pitchDegrees": 0.0, "lensMm": CAMERA.data.lens,
            "fovHalfX": CALIBRATION["fovHalfX"], "eye": list(CAMERA_EYE),
        },
        "anchors": sorted(o.name for o in col("TH_ANCHORS").objects),
        "collections": {n: len(col(n).objects) for n in COLLECTION_NAMES},
    }
    (ATTEMPTS / ("attempt_%s.json" % attempt_id)).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def make_atlas_from_source(source_path: Path, atlas_path: Path):
    # A native-resolution source beauty render is promoted to a single
    # camera-space atlas. A dark upper band is reserved for coarse foreground
    # occluders in the OBJ runtime package. No previous texture participates.
    src = bpy.data.images.load(str(source_path.resolve()), check_existing=False)
    atlas = bpy.data.images.new("CleanroomBeautyAtlas", width=1024, height=1024, alpha=True)
    source_px = list(src.pixels[:])
    out = [0.015, 0.012, 0.010, 1.0] * (1024 * 1024)
    region_h = 576
    for y in range(region_h):
        sy = min(H - 1, int(y * H / region_h))
        for x in range(1024):
            sx = min(W - 1, int(x * W / 1024))
            si = (sy * W + sx) * 4
            # Blender's pixel array and UV origin are both bottom-up here.
            di = (y * 1024 + x) * 4
            out[di:di+4] = source_px[si:si+4]
    atlas.pixels.foreach_set(out)
    atlas.filepath_raw = str(atlas_path)
    atlas.file_format = "PNG"
    atlas.save()
    bpy.data.images.remove(src)
    return atlas


def image_plane(atlas, depth=18.2):
    ax = CALIBRATION["projectionScale"]["x"] / CALIBRATION["fovHalfX"] * (256.0 / W)
    ay = CALIBRATION["projectionScale"]["y"] / CALIBRATION["fovHalfY"] * (144.0 / H)
    half_w, half_h = depth / ax, depth / ay
    me = bpy.data.meshes.new("runtime_beauty_plane_mesh")
    me.from_pydata([(-half_w,-half_h,0),(half_w,-half_h,0),(half_w,half_h,0),(-half_w,half_h,0)], [], [(0,1,2,3)])
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    # Source render occupies the bottom 576 rows of the atlas.
    coords = [(0.0,0.0),(1.0,0.0),(1.0,0.5625),(0.0,0.5625)]
    for loop in me.loops:
        uv.data[loop.index].uv = coords[loop.vertex_index]
    mat = bpy.data.materials.new("EnvironmentBakedAtlas")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = atlas
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    emit.inputs["Strength"].default_value = 1.0
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    me.materials.append(mat)
    ob = bpy.data.objects.new("runtime_beauty_atlas_plane", me)
    col("TH_RENDER").objects.link(ob)
    ob.location = (CAMERA_EYE[0] + depth, 5.5, 0.0)
    ob.rotation_mode = "QUATERNION"
    # Keep the atlas upright; the camera's reflected projection basis is not
    # a valid billboard rotation for image-space geometry.
    ob.rotation_quaternion = Matrix(((0.0, 0.0, 1.0),
                                     (1.0, 0.0, 0.0),
                                     (0.0, 1.0, 0.0))).to_quaternion()
    ob["bake_kind"] = "camera-space beauty atlas from selected TH_SOURCE"
    return ob


def export_obj(objects, path: Path, include_mtl=True, plane_name="runtime_beauty_atlas_plane"):
    lines = ["# Second Rite clean-room runtime package", "mtllib environment.mtl" if include_mtl else ""]
    vs, vts, faces = [], [], []
    for ob in objects:
        if ob.type != "MESH":
            continue
        mesh = ob.data
        base_v = len(vs) + 1
        base_t = len(vts) + 1
        for v in mesh.vertices:
            p = ob.matrix_world @ v.co
            vs.append((p.x, p.y, p.z))
        if ob.name == plane_name:
            uv_layer = mesh.uv_layers.active
            per_vertex = [(0.0,0.0)] * len(mesh.vertices)
            for poly in mesh.polygons:
                for li in poly.loop_indices:
                    per_vertex[mesh.loops[li].vertex_index] = tuple(uv_layer.data[li].uv)
            vts.extend(per_vertex)
        else:
            # Dark upper-band patch in the single atlas.
            vts.extend([(0.01,0.88)] * len(mesh.vertices))
        for poly in mesh.polygons:
            idxs = []
            for vi in poly.vertices:
                idxs.append((base_v + vi, base_t + vi))
            faces.append(idxs)
    for x, y, z in vs:
        lines.append("v %.6f %.6f %.6f" % (x, y, z))
    for u, v in vts:
        lines.append("vt %.6f %.6f" % (u, v))
    lines.append("g Environment")
    if include_mtl:
        lines.append("usemtl EnvironmentBakedAtlas")
    for face in faces:
        lines.append("f " + " ".join("%d/%d" % p for p in face))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(vs), sum(max(0, len(f) - 2) for f in faces)


def export_collision(path: Path):
    objs = [o for o in col("TH_COLLISION").objects if o.type == "MESH"]
    old = []
    lines = ["# Clean-room collision proof mesh"]
    idx = 1
    for ob in objs:
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            lines.append("v %.6f %.6f %.6f" % (p.x, p.y, p.z))
        for poly in ob.data.polygons:
            lines.append("f " + " ".join(str(idx + vi) for vi in poly.vertices))
        idx += len(ob.data.vertices)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_runtime_package(attempt_record, atlas_path: Path):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    render_objects = [o for o in col("TH_RENDER").objects if o.type == "MESH"]
    verts, tris = export_obj(render_objects, RUNTIME / "environment.obj")
    export_collision(RUNTIME / "collision.obj")
    (RUNTIME / "environment.mtl").write_text(
        "newmtl EnvironmentBakedAtlas\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nmap_Kd environment.png\n", encoding="utf-8")
    atlas_dest = RUNTIME / "environment.png"
    # Blender's bundled Windows Python can reject copy2 when the destination
    # is an existing image datablock path. Replace this exact package file
    # explicitly after the prior run has released it.
    if atlas_dest.exists():
        atlas_dest.unlink()
    shutil.copyfile(str(atlas_path), str(atlas_dest))
    anchors = {}
    for o in col("TH_ANCHORS").objects:
        anchors[o.name] = {"id": o.name, "position": list(o.location), "forward": [1.0, 0.0, 0.0], "kind": o.get("kind", "point")}
    manifest = {
        "contractVersion": 1,
        "renderMesh": "environment.obj",
        "materialLibrary": "environment.mtl",
        "textureAtlas": "environment.png",
        "collisionMesh": "collision.obj",
        "stats": {"triangleCount": tris, "vertexCount": verts, "materialGroupCount": 1, "textureDimensions": [1024,1024]},
        "bounds": {"min": [3.3, 1.45, -1.7], "max": [8.7, 9.55, 6.8]},
        "anchors": anchors,
        "camera": CALIBRATION,
        "sourceAttempt": attempt_record["id"],
        "bake": {"kind": "camera-space beauty bake", "source": "TH_SOURCE", "target": "TH_RENDER", "previewActorsExcluded": True},
    }
    (RUNTIME / "environment.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run_selected(winner: str, record):
    scene = reset_scene()
    title, concept = BUILDERS[winner]()
    # Re-author the winner from empty state, as required for convergence/final selection.
    source_triangles = tri_count("TH_SOURCE")
    author_runtime_shape(winner)
    configure_source_render()
    source_env = OUT / "selected_source_beauty.png"
    col("TH_PREVIEW_ACTORS").hide_render = True
    render(source_env)
    atlas_path = OUT / "town-cleanroom-beauty-atlas.png"
    atlas = make_atlas_from_source(source_env, atlas_path)
    col("TH_PREVIEW_ACTORS").hide_render = False
    col("TH_SOURCE").hide_render = True
    col("TH_RENDER").hide_render = False
    image_plane(atlas)
    # Runtime image plane is the coarse backdrop; the authored occluder remains real geometry.
    runtime_env = OUT / "selected_runtime_environment.png"
    col("TH_PREVIEW_ACTORS").hide_render = True
    for o in col("TH_RENDER").objects:
        if o.name != "runtime_beauty_atlas_plane":
            o.hide_render = True
    render(runtime_env)
    for o in col("TH_RENDER").objects:
        o.hide_render = False
    col("TH_PREVIEW_ACTORS").hide_render = False
    runtime_full = OUT / "selected_runtime_full.png"
    render(runtime_full)
    render_triangles = tri_count("TH_RENDER")
    manifest = export_runtime_package({**record, "sourceTris": source_triangles, "renderTris": render_triangles}, atlas_path)
    projection_paths = []
    for label, off in [("left", -96.0), ("center", 0.0), ("right", 96.0)]:
        CAMERA.data.shift_x = BASE_CAMERA_SHIFT[0] + off / W
        CAMERA.data.shift_y = BASE_CAMERA_SHIFT[1]
        p = OUT / ("projection_%s.png" % label)
        render(p)
        projection_paths.append(str(p))
    CAMERA.data.shift_x, CAMERA.data.shift_y = BASE_CAMERA_SHIFT
    save_blend(OUT / "selected_winner_source.blend")
    final = {
        "winner": winner, "title": title, "concept": concept,
        "sourceTris": source_triangles, "renderTris": render_triangles,
        "reductionRatio": source_triangles / max(1, render_triangles),
        "actorHeightPx": project_actor_measurement(), "atlas": {"path": str(atlas_path), "dimensions": [1024,1024], "bytes": atlas_path.stat().st_size},
        "runtimePackageBytes": sum(p.stat().st_size for p in RUNTIME.iterdir() if p.is_file()),
        "projectionStrip": projection_paths,
        "camera": {"eye": list(CAMERA_EYE), "lensMm": CAMERA.data.lens, "pitchDegrees": 0.0, "fovDegrees": math.degrees(2*math.atan(CALIBRATION["fovHalfX"]))},
        "manifest": manifest,
    }
    (OUT / "selected.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    return final


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ATTEMPTS.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    run_material_test()
    records = []
    for aid in ["01","02","03","04","05","06","07","08","09"]:
        print("CLEANROOM_ATTEMPT_START", aid, flush=True)
        records.append(run_attempt(aid))
        print("CLEANROOM_ATTEMPT_DONE", aid, records[-1]["sourceTris"], records[-1]["renderTris"], flush=True)
    (OUT / "census.json").write_text(json.dumps({r["id"]: r for r in records}, indent=2), encoding="utf-8")
    # Selection is intentionally a post-render decision; the current run uses
    # an explicit placeholder until blind visual scoring writes winner.txt.
    winner_file = OUT / "winner.txt"
    winner = winner_file.read_text(encoding="utf-8").strip() if winner_file.is_file() else "04"
    if winner not in BUILDERS:
        raise ValueError("winner.txt must contain one of 01..09")
    selected = run_selected(winner, next(r for r in records if r["id"] == winner))
    print("CLEANROOM_SELECTED", json.dumps({k:selected[k] for k in ["winner","sourceTris","renderTris","reductionRatio","actorHeightPx"]}), flush=True)


if __name__ == "__main__":
    main()
