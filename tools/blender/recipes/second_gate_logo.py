import bpy
import math
from pathlib import Path
from mathutils import Vector


OUT_DIR = Path(r"D:\Antigravity\Hichaukitoden\projects\hichaukitoden-game\assets\authoring\title")
BLEND_PATH = OUT_DIR / "second-gate-logo-codex.blend"
PREVIEW_PATH = OUT_DIR / "second-gate-logo-codex-preview.png"


def material(name, color, emission=0.0, metallic=0.0, roughness=0.35):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def text_object(name, body, size, location, font_path, mat, extrude=0.035, bevel=0.012, spacing=1.0):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.space_character = spacing
    curve.extrude = extrude
    curve.bevel_depth = bevel
    curve.bevel_resolution = 5
    if font_path.exists():
        curve.font = bpy.data.fonts.load(str(font_path))
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def poly_curve(name, points, bevel, mat, z=0.0, cyclic=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.bevel_depth = bevel
    curve.bevel_resolution = 6
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, (x, y) in zip(spline.bezier_points, points):
        bp.co = (x, y, z)
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def parent_to(obj, parent):
    obj.parent = parent
    return obj


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.curves, bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
scene.render.filepath = str(PREVIEW_PATH)
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.look = "Medium High Contrast"
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 240
scene.world.color = (0.001, 0.001, 0.002)

white = material("Ivory lettering", (1.0, 0.98, 0.92), emission=1.4, metallic=0.1, roughness=0.25)
edge = material("Warm edge", (0.42, 0.025, 0.012), emission=1.5, roughness=0.3)
red = material("Gate energy", (1.0, 0.015, 0.003), emission=8.0, roughness=0.22)
red_dim = material("Gate core", (0.18, 0.001, 0.001), emission=1.8, roughness=0.5)
teal = material("Brush teal", (0.0, 0.34, 0.27), emission=0.45, metallic=0.05, roughness=0.65)

rig = bpy.data.objects.new("LOGO_RIG", None)
bpy.context.collection.objects.link(rig)
type_rig = bpy.data.objects.new("TYPE_RIG", None)
vortex_rig = bpy.data.objects.new("VORTEX_RIG", None)
brush_rig = bpy.data.objects.new("BRUSH_RIG", None)
for empty in (type_rig, vortex_rig, brush_rig):
    bpy.context.collection.objects.link(empty)
    empty.parent = rig

# Red dimensional underlay gives the letters a carved, glowing edge.
font = Path(r"C:\Windows\Fonts\timesbd.ttf")
small_font = Path(r"C:\Windows\Fonts\times.ttf")
shadow_second = text_object("SECOND_edge", "SECOND", 0.86, (0, 0.58, -0.03), font, edge, 0.045, 0.018)
shadow_gate = text_object("GATE_edge", "GATE", 1.72, (0, -0.57, -0.03), font, edge, 0.06, 0.025)
second = text_object("SECOND", "SECOND", 0.82, (0, 0.64, 0.08), small_font, white, 0.045, 0.012)
gate = text_object("GATE", "GATE", 1.62, (0, -0.50, 0.09), font, white, 0.055, 0.016)
for obj in (shadow_second, shadow_gate, second, gate):
    parent_to(obj, type_rig)

# A three-turn, deliberately uneven energy spiral matching the concept's red sweep.
spiral = []
for i in range(150):
    t = i / 149 * math.tau * 2.35
    r = 0.42 + 0.12 * t
    spiral.append((math.cos(t) * r * 1.30, math.sin(t) * r * 0.50))
energy = parent_to(poly_curve("Energy spiral", spiral, 0.027, red, z=-0.16), vortex_rig)
core = parent_to(poly_curve("Energy core", spiral[20:-8], 0.065, red_dim, z=-0.21), vortex_rig)

# Teal calligraphic gate mark, built from editable Bezier strokes rather than a flat image.
strokes = [
    [(-3.30, -1.45), (-3.08, 0.25), (-2.72, 1.55), (-2.44, 0.55), (-2.66, -1.15)],
    [(-2.62, 0.52), (-2.13, 1.12), (-1.70, 0.75), (-1.85, -1.18), (-1.25, -1.62)],
    [(-1.56, 1.13), (-1.00, 1.45), (-0.65, 0.58), (-0.74, -1.28)],
    [(-0.62, -1.16), (-0.15, 1.25), (0.58, 1.34), (0.34, -1.36), (-0.33, -1.64)],
    [(0.58, 1.15), (1.17, 1.42), (1.05, -1.08), (0.70, -1.42)],
    [(1.38, 1.34), (1.75, 0.86), (1.65, -1.08), (1.25, -1.48)],
    [(1.98, 1.18), (2.52, 0.82), (2.62, -1.18), (2.04, -1.42)],
    [(2.55, 0.90), (3.10, 0.45), (3.25, -0.85), (2.85, -1.35)],
]
for i, pts in enumerate(strokes):
    stroke = poly_curve(f"Brush stroke {i+1:02d}", pts, 0.060 if i % 3 else 0.045, teal, z=-0.10)
    parent_to(stroke, brush_rig)

# Animation-ready defaults: slow vortex rotation, brush reveal proxy, subtle title breathing.
vortex_rig.rotation_euler.z = 0
vortex_rig.keyframe_insert("rotation_euler", frame=1, index=2)
vortex_rig.rotation_euler.z = math.tau
vortex_rig.keyframe_insert("rotation_euler", frame=241, index=2)
type_rig.scale = (1, 1, 1)
type_rig.keyframe_insert("scale", frame=1)
type_rig.scale = (1.018, 1.018, 1.018)
type_rig.keyframe_insert("scale", frame=120)
type_rig.scale = (1, 1, 1)
type_rig.keyframe_insert("scale", frame=240)

camera_data = bpy.data.cameras.new("Logo Camera")
camera = bpy.data.objects.new("Logo Camera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (0, 0, 10)
camera.rotation_euler = (0, 0, 0)
camera_data.type = "ORTHO"
camera_data.ortho_scale = 8.25
scene.camera = camera

bpy.context.scene.frame_set(45)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
bpy.ops.render.render(write_still=True)
print(f"Saved {BLEND_PATH}")
print(f"Rendered {PREVIEW_PATH}")
