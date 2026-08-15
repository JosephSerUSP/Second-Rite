"""Build five non-canonical editable Blender item-authoring specimens.

The point of this study is not another OBJ cohort.  Each .blend must preserve a
useful, human-editable construction graph while the game still receives a
flattened OBJ/MTL product through the shared exporter.

Specimens:
- study_screw_reliquary: A-like revolved/profile construction.
- study_fabricated_mask: B-like planar fabrication with live boolean cutters.
- study_curve_fang: C-like editable spatial curve with authored taper.
- study_segmented_spine: fabricated segment repeated along a curve with modifiers.
- study_phoenix_pinion: A+B+C hybrid, including repeated/tapered vanes along a curve.

Generated files are intentionally study-only and do not replace canonical item
models or database paths.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

import second_rite_asset_core as asset_core

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "assets" / "authoring" / "items" / "studies" / "blender_editable"
MODEL_DIR = ROOT / "assets" / "models" / "items" / "studies" / "blender_editable"
REPORT_DIR = ROOT / "docs" / "reports" / "blender-item-authoring-study"
PREVIEW_DIR = REPORT_DIR / "previews"
MANIFEST = REPORT_DIR / "generated-manifest.json"

for directory in (SOURCE_DIR, MODEL_DIR, PREVIEW_DIR):
    directory.mkdir(parents=True, exist_ok=True)

MATERIAL_IDS = [
    "aged_cloth",
    "bone",
    "crystal",
    "dark_wood",
    "oxidized_bronze",
    "ritual_gold",
    "wrought_iron",
]


def reset():
    asset_core.reset_scene(factory=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 384
    scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.world.color = (0.025, 0.025, 0.025)
    return scene


def materials():
    return {mid: asset_core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}


def root_for(item_id: str, description: str):
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.25
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = item_id
    root["study_authoring_description"] = description
    asset_core.tag_asset_target(
        root,
        asset_id=item_id,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
        states=["default"],
        default_state="default",
        variants=[],
        extra={"sr_study_only": True, "sr_source_authority": "blend"},
    )
    return root


def mesh_object(name, vertices, edges=(), faces=(), *, parent=None, material=None):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, edges, faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        asset_core.parent_local(obj, parent)
    if material is not None:
        asset_core.assign_material(obj, material)
    return obj


def profile_screw(name, profile, *, axis="Z", parent, material, steps=12, bevel=0.025):
    """Create an editable profile edge-chain with an unapplied Screw modifier."""
    axis = axis.upper()
    if axis == "Z":
        vertices = [(radius, 0.0, height) for radius, height in profile]
    elif axis == "X":
        vertices = [(height, radius, 0.0) for radius, height in profile]
    else:
        raise ValueError(axis)
    edges = [(i, i + 1) for i in range(len(vertices) - 1)]
    obj = mesh_object(name, vertices, edges=edges, parent=parent, material=material)
    screw = obj.modifiers.new("A_ProfileRevolve", "SCREW")
    screw.axis = axis
    screw.angle = math.tau
    screw.steps = steps
    screw.render_steps = steps
    screw.use_merge_vertices = True
    screw.merge_threshold = 0.0001
    screw.use_smooth_shade = True
    if bevel > 0:
        asset_core.add_bevel_modifier(obj, width=bevel, segments=1, name="FinishBevel", angle_degrees=25.0)
    return obj


def plate(name, points_xy, *, parent, material, thickness=0.08, bevel=0.025, z=0.0):
    vertices = [(x, y, z) for x, y in points_xy]
    obj = mesh_object(name, vertices, faces=[tuple(range(len(vertices)))], parent=parent, material=material)
    solid = obj.modifiers.new("B_Thickness", "SOLIDIFY")
    solid.thickness = thickness
    solid.offset = 0.0
    if bevel > 0:
        asset_core.add_bevel_modifier(obj, width=bevel, segments=1, name="FinishBevel", angle_degrees=25.0)
    return obj


def cutter_cylinder(name, *, parent, radius, depth, location):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["study_helper"] = "boolean_cutter"
    return obj


def path_curve(name, points, *, parent, material, bevel_depth=0.08, radii=None):
    curve = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.resolution_v = 0
    curve.bevel_resolution = 0
    curve.bevel_depth = bevel_depth
    curve.resolution_u = 1
    curve.fill_mode = "FULL"
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    radii = radii or [1.0] * len(points)
    for point, radius, target in zip(points, radii, spline.points):
        target.co = (*point, 1.0)
        target.radius = radius
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    asset_core.assign_material(obj, material)
    return obj


def x_path(name, points, *, parent):
    curve = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = 0.0
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, target in zip(points, spline.points):
        target.co = (*point, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    asset_core.parent_local(obj, parent)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["study_helper"] = "deformation_path"
    return obj


def repeated_plate_along_curve(name, points_xy, *, parent, material, path, count, offset,
                               thickness=0.05, taper=0.0):
    obj = plate(name, points_xy, parent=parent, material=material, thickness=thickness, bevel=0.015)
    array = obj.modifiers.new("ComposeRepeat", "ARRAY")
    array.use_relative_offset = False
    array.use_constant_offset = True
    array.constant_offset_displace = (offset, 0.0, 0.0)
    array.count = count
    if taper:
        deform = obj.modifiers.new("ComposeTaper", "SIMPLE_DEFORM")
        deform.deform_method = "TAPER"
        deform.deform_axis = "X"
        deform.factor = taper
    curve = obj.modifiers.new("ComposeAlongCurve", "CURVE")
    curve.object = path
    curve.deform_axis = "POS_X"
    return obj


def add_preview_rig(root):
    bpy.ops.object.light_add(type="AREA", location=(-3.0, -4.0, 5.0))
    key = bpy.context.object
    key.name = "PREVIEW_Key"
    key.data.energy = 800.0
    key.data.shape = "DISK"
    key.data.size = 4.0

    bpy.ops.object.light_add(type="AREA", location=(4.0, 1.5, 2.0))
    fill = bpy.context.object
    fill.name = "PREVIEW_Fill"
    fill.data.energy = 350.0
    fill.data.size = 3.0

    bpy.ops.object.camera_add(location=(4.5, -6.5, 3.2))
    camera = bpy.context.object
    camera.name = "PREVIEW_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.1
    bpy.context.scene.camera = camera

    def point_at(obj, target=(0.0, 0.0, 0.0)):
        direction = Vector(target) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    point_at(camera)
    point_at(key)
    point_at(fill)


def render_views(item_id, root):
    scene = bpy.context.scene
    original = root.rotation_euler.copy()
    views = [
        ("front", (0.0, 0.0, 0.0)),
        ("three_quarter", (math.radians(12), 0.0, math.radians(55))),
        ("side", (0.0, 0.0, math.radians(90))),
        ("top", (math.radians(72), 0.0, math.radians(30))),
    ]
    for label, rotation in views:
        root.rotation_euler = rotation
        bpy.context.view_layer.update()
        scene.render.filepath = str(PREVIEW_DIR / f"{item_id}-{label}.png")
        bpy.ops.render.render(write_still=True)
    root.rotation_euler = original
    bpy.context.view_layer.update()


def embed_note(item_id, note):
    text = bpy.data.texts.get("AUTHORING_README") or bpy.data.texts.new("AUTHORING_README")
    text.clear()
    text.write(
        f"Editable item-authoring study: {item_id}\n\n"
        f"{note}\n\n"
        "The .blend is intentional source material. Important modifiers/curves are left unapplied.\n"
        "The runtime OBJ is compiled from a temporary evaluated duplicate through second_rite_asset_core.py.\n"
        "Generated study assets do not replace canonical game item models.\n"
    )


def build_screw_reliquary(mat):
    root = root_for("study_screw_reliquary", "A-like profile revolution kept live through Screw modifiers")
    body_profile = [
        (0.58, -0.78), (0.75, -0.68), (0.82, -0.48), (0.72, 0.15),
        (0.52, 0.48), (0.31, 0.67), (0.26, 0.58), (0.40, 0.38),
        (0.54, 0.10), (0.61, -0.44), (0.50, -0.62), (0.58, -0.78),
    ]
    profile_screw("A_BodyProfile", body_profile, parent=root, material=mat["oxidized_bronze"], steps=14)
    crown_profile = [(0.09, 0.55), (0.25, 0.68), (0.18, 0.82), (0.06, 0.94)]
    profile_screw("A_CrownProfile", crown_profile, parent=root, material=mat["ritual_gold"], steps=10)
    return root, "Edit the sparse profile meshes; Screw + Bevel remain live."


def build_fabricated_mask(mat):
    root = root_for("study_fabricated_mask", "B-like planar fabrication with live thickness, bevel and boolean holes")
    shell = plate(
        "B_MaskShell",
        [(-0.82, -0.18), (-0.66, 0.43), (-0.20, 0.70), (0.20, 0.70),
         (0.66, 0.43), (0.82, -0.18), (0.34, -0.67), (-0.34, -0.67)],
        parent=root, material=mat["wrought_iron"], thickness=0.13, bevel=0.035,
    )
    for side in (-1, 1):
        cutter = cutter_cylinder(
            f"B_LensCutter_{side:+d}", parent=root, radius=0.27, depth=0.7,
            location=(side * 0.36, 0.15, 0.0),
        )
        boolean = shell.modifiers.new(f"B_LensHole_{side:+d}", "BOOLEAN")
        boolean.operation = "DIFFERENCE"
        boolean.solver = "EXACT"
        boolean.object = cutter
    plate("B_BrowPlate", [(-0.57, 0.40), (0.57, 0.40), (0.43, 0.54), (-0.43, 0.54)],
          parent=root, material=mat["ritual_gold"], thickness=0.16, bevel=0.025, z=0.03)
    return root, "Lens openings are live Boolean cutters; silhouette and thickness remain editable."


def build_curve_fang(mat):
    root = root_for("study_curve_fang", "C-like spatial gesture represented by editable Curve splines and point radii")
    path_curve(
        "C_FangPath",
        [(-0.25, 0.0, -0.85), (-0.16, 0.04, -0.45), (0.02, 0.10, -0.05),
         (0.28, 0.06, 0.33), (0.42, -0.05, 0.67), (0.31, -0.13, 0.94)],
        parent=root, material=mat["bone"], bevel_depth=0.19,
        radii=[1.0, 0.95, 0.82, 0.62, 0.38, 0.09],
    )
    scar = path_curve(
        "C_GoldScar",
        [(0.05, -0.16, 0.18), (0.16, -0.18, 0.30), (0.27, -0.17, 0.44)],
        parent=root, material=mat["ritual_gold"], bevel_depth=0.025,
        radii=[1.0, 0.9, 0.65],
    )
    scar.data.resolution_u = 1
    return root, "Move curve points and edit per-point radius; the exported tube is evaluated only at compile time."


def build_segmented_spine(mat):
    root = root_for("study_segmented_spine", "B structure duplicated along a C path with Array + Curve modifiers")
    path = x_path(
        "C_SpineGuide",
        [(-1.0, 0.0, -0.25), (-0.55, 0.04, -0.08), (-0.10, -0.08, 0.10),
         (0.40, 0.06, 0.28), (0.95, 0.0, 0.17)],
        parent=root,
    )
    repeated_plate_along_curve(
        "B_VertebraSource",
        [(-1.02, -0.25), (-0.92, -0.48), (-0.80, -0.22), (-0.89, 0.0),
         (-0.80, 0.22), (-0.92, 0.48), (-1.02, 0.25)],
        parent=root, material=mat["bone"], path=path, count=10, offset=0.20,
        thickness=0.07, taper=-0.18,
    )
    path_curve(
        "C_SpineCord",
        [(-1.03, 0.0, -0.25), (-0.55, 0.04, -0.08), (-0.10, -0.08, 0.10),
         (0.40, 0.06, 0.28), (0.95, 0.0, 0.17)],
        parent=root, material=mat["dark_wood"], bevel_depth=0.055,
        radii=[1.0, 0.95, 0.8, 0.65, 0.45],
    )
    return root, "One fabricated vertebra is repeated, tapered and deformed by an editable guide curve."


def build_phoenix_pinion(mat):
    root = root_for("study_phoenix_pinion", "A+B+C hybrid: revolved clasp, swept rachis and fabricated vanes repeated along curve")
    guide_points = [
        (-1.05, 0.0, -0.18), (-0.65, 0.04, -0.05), (-0.18, -0.02, 0.10),
        (0.30, 0.07, 0.25), (0.78, 0.02, 0.36), (1.18, -0.06, 0.33),
    ]
    guide = x_path("C_RachisGuide", guide_points, parent=root)
    path_curve(
        "C_Rachis",
        guide_points,
        parent=root, material=mat["ritual_gold"], bevel_depth=0.055,
        radii=[1.1, 1.0, 0.9, 0.72, 0.48, 0.22],
    )

    left = [(-1.08, 0.06), (-1.00, 0.70), (-0.88, 0.86), (-0.82, 0.18)]
    right = [(x, -y) for x, y in left]
    repeated_plate_along_curve(
        "B_LeftVaneSource", left, parent=root, material=mat["aged_cloth"], path=guide,
        count=9, offset=0.235, thickness=0.045, taper=-0.42,
    )
    repeated_plate_along_curve(
        "B_RightVaneSource", right, parent=root, material=mat["aged_cloth"], path=guide,
        count=9, offset=0.235, thickness=0.045, taper=-0.42,
    )

    clasp_profile = [(0.27, -1.12), (0.34, -1.02), (0.31, -0.88), (0.22, -0.78),
                     (0.16, -0.84), (0.20, -1.02), (0.27, -1.12)]
    clasp = profile_screw(
        "A_PinionClaspProfile", clasp_profile, axis="X", parent=root,
        material=mat["oxidized_bronze"], steps=10, bevel=0.02,
    )
    clasp.rotation_euler[1] = math.radians(90)

    plate(
        "B_EmberTip", [(1.05, -0.10), (1.42, 0.0), (1.05, 0.10), (0.95, 0.0)],
        parent=root, material=mat["crystal"], thickness=0.10, bevel=0.02, z=0.34,
    )
    return root, "Hybrid source: A clasp profile, C rachis/guide, and B vane sources with live repeat+taper+curve stacks."


BUILDERS = [
    build_screw_reliquary,
    build_fabricated_mask,
    build_curve_fang,
    build_segmented_spine,
    build_phoenix_pinion,
]


def structural_summary(item_id, root):
    children = list(root.children_recursive)
    modifier_types = sorted({modifier.type for obj in children for modifier in getattr(obj, "modifiers", [])})
    return {
        "id": item_id,
        "root": root.name,
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "hiddenFromRender": bool(obj.hide_render),
                "modifiers": [modifier.type for modifier in getattr(obj, "modifiers", [])],
            }
            for obj in children
        ],
        "modifierTypes": modifier_types,
        "curveCount": sum(1 for obj in children if obj.type == "CURVE"),
        "meshCount": sum(1 for obj in children if obj.type == "MESH"),
    }


def build_all():
    summaries = []
    for builder in BUILDERS:
        reset()
        mat = materials()
        root, note = builder(mat)
        item_id = root["item_export_name"]
        embed_note(item_id, note)
        add_preview_rig(root)
        bpy.context.view_layer.update()

        render_views(item_id, root)

        blend_path = SOURCE_DIR / f"{item_id}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

        outputs = asset_core.export_asset_root(
            bpy.context,
            root,
            MODEL_DIR,
            export_shape_keys=False,
            center_mode="PIVOT",
        )
        if len(outputs) != 1:
            raise RuntimeError(f"{item_id}: expected one OBJ, got {outputs}")

        summary = structural_summary(item_id, root)
        summary["blend"] = str(blend_path.relative_to(ROOT))
        summary["runtimeObj"] = str(Path(outputs[0]).relative_to(ROOT))
        summary["authoringNote"] = note
        summaries.append(summary)
        print(f"BUILT {item_id}: {summary['modifierTypes']} curves={summary['curveCount']}")

    MANIFEST.write_text(
        json.dumps({"study": "blender-editable-item-authoring", "items": summaries}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {MANIFEST}")


if __name__ == "__main__":
    build_all()
