"""Add the authored Cortiço composition pass to the adopted source blend.

This is an explicit source-edit tool, not a regeneration path. It preserves the
existing buildings, floor grid, anchors, camera and packed background cards,
and adds ordinary exported meshes for the shared courtyard life of a subdivided
grand house: thresholds, lean-tos, laundry, low masonry, planting and the
workers' stair/padaria service approach.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


LANE_CENTRE = 12.031
REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNDRY_TEXTURE = REPO_ROOT / (
    "projects/hichaukitoden-game/assets/materials/cortico_laundry_quad.png")


def by(runtime_y: float) -> float:
    """Convert an engine lane position into the adopted Blender mirror."""
    return LANE_CENTRE - float(runtime_y)


def collection(name: str):
    source = bpy.data.collections.get("TH_SOURCE")
    if source is None:
        raise RuntimeError("adopted source is missing TH_SOURCE")
    target = bpy.data.collections.get(name)
    if target is None:
        target = bpy.data.collections.new(name)
        source.children.link(target)
    return target


def material(name: str, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.9
        mat.diffuse_color = (*color, 1.0)
    return mat


def image_material(name: str, image_path: Path):
    """Create a packed alpha billboard material for a single authored quad."""
    if not image_path.is_file():
        raise RuntimeError(f"laundry texture not found: {image_path}")
    # Replace any prior packed datablock with the same filename. Reusing it
    # would silently retain an older RGB/checker version after the source art
    # has been regenerated with real alpha.
    old_image = bpy.data.images.get(image_path.name)
    if old_image is not None:
        bpy.data.images.remove(old_image)
    image = bpy.data.images.load(str(image_path), check_existing=False)
    if image.packed_file is None:
        image.pack()
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    shader.inputs["Roughness"].default_value = 0.92
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    try:
        mat.surface_render_method = "DITHERED"
    except (AttributeError, TypeError, ValueError):
        pass
    mat.diffuse_color = (0.65, 0.5, 0.35, 1.0)
    return mat


def link_only(obj, target):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)


def tag(obj, role):
    obj["sr_export"] = True
    obj["sr_authored_detail"] = True
    obj["sr_source_role"] = role
    return obj


def box(name, location, size, mat, target, role):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_only(obj, target)
    obj.data.materials.append(mat)
    return tag(obj, role)


def face(name, x, y0, y1, z0, z1, mat, target, role):
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)],
                     [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    mesh.materials.append(mat)
    return tag(obj, role)


def laundry_quad(name, x, runtime_y0, runtime_y1, z0, z1, mat, target):
    """One camera-facing quad carrying poles, wire and hanging laundry."""
    y0 = by(runtime_y0)
    y1 = by(runtime_y1)
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(
        [(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)],
        [], [(0, 1, 2, 3)])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.polygons[0].loop_indices:
        uv.data[loop].uv = ((0.0, 0.0), (0.0, 1.0),
                            (1.0, 1.0), (1.0, 0.0))[loop]
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    mesh.materials.append(mat)
    return tag(obj, "shared_laundry_image_quad")


def clear_previous():
    for obj in list(bpy.data.objects):
        if obj.name.startswith("CORTICO_AUTHORED_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def build(blend: Path):
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    clear_previous()
    foreground = collection("21_FOREGROUND")
    architecture = collection("20_ARCHITECTURE")
    props = collection("30_PROPS")

    stone = bpy.data.materials.get("sr_rough_limestone") or material(
        "sr_rough_limestone", (0.48, 0.42, 0.33))
    old_stone = bpy.data.materials.get("sr_old_limestone") or material(
        "sr_old_limestone", (0.58, 0.52, 0.42))
    whitewash = bpy.data.materials.get("sr_whitewash") or material(
        "sr_whitewash", (0.68, 0.63, 0.52))
    roof = bpy.data.materials.get("sr_roof_tile") or material(
        "sr_roof_tile", (0.38, 0.16, 0.08))
    wood = bpy.data.materials.get("sr_dark_wood") or material(
        "sr_dark_wood", (0.18, 0.10, 0.06))
    iron = bpy.data.materials.get("sr_wrought_iron") or material(
        "sr_wrought_iron", (0.08, 0.09, 0.08))
    fabric_a = material("sr_laundry_faded_blue", (0.25, 0.38, 0.43))
    fabric_b = material("sr_laundry_ochre", (0.56, 0.40, 0.20))
    fabric_c = material("sr_laundry_rose", (0.48, 0.25, 0.23))
    plant = bpy.data.materials.get("sr_foliage_card") or material(
        "sr_foliage_card", (0.12, 0.24, 0.10))
    laundry_quad_mat = image_material("sr_cortico_laundry_quad", LAUNDRY_TEXTURE)

    # The grand-house reading: a patched gallery line and several independent
    # thresholds, not another symmetric standalone facade.
    for index, runtime_y in enumerate((-7.5, -1.0, 6.5, 14.0, 21.5)):
        box(f"CORTICO_AUTHORED_SUBDIVISION_PIER_{index}",
            (14.55, by(runtime_y), 2.35), (.32, .30, 4.7), stone,
            architecture, "subdivided_grand_house_pier")
        box(f"CORTICO_AUTHORED_SUBDIVISION_DOOR_{index}",
            (14.35, by(runtime_y), 1.10), (.18, .95, 2.2), wood,
            architecture, "household_threshold")
        box(f"CORTICO_AUTHORED_SUBDIVISION_LINTEL_{index}",
            (14.25, by(runtime_y), 2.35), (.24, 1.35, .22), old_stone,
            architecture, "patched_threshold")
    for index, runtime_y in enumerate((-4.2, 8.0, 17.0)):
        box(f"CORTICO_AUTHORED_LEANTO_ROOF_{index}",
            (13.55, by(runtime_y), 4.45), (1.45, 3.8, .20), roof,
            architecture, "irregular_lean_to")
        box(f"CORTICO_AUTHORED_LEANTO_WALL_{index}",
            (14.05, by(runtime_y), 2.25), (.24, 3.4, 3.7), whitewash,
            architecture, "irregular_lean_to")

    # Shared courtyard facility: a low basin, two posts and laundry in front
    # of it. The pieces stay narrow enough that the actors and arrows remain
    # legible in both town surfaces.
    box("CORTICO_AUTHORED_WASH_BASIN", (8.15, by(7.4), .28),
        (1.25, 1.45, .56), old_stone, props, "shared_washing_basin")
    box("CORTICO_AUTHORED_WASH_INNER", (7.78, by(7.4), .58),
        (.48, .90, .12), iron, props, "shared_washing_basin")
    laundry = laundry_quad("CORTICO_AUTHORED_LAUNDRY_QUAD", 4.25, 5.3, 10.9,
                           .45, 3.55, laundry_quad_mat, props)
    # The image carries alpha and must remain an independent placed model;
    # baking it into the opaque beauty atlas would turn transparent pixels
    # into a rectangular slab. It is still one source quad and one runtime
    # draw, just on the same world-space layer path as the distant cards.
    laundry["sr_export"] = False
    laundry["sr_background_layer"] = True
    laundry["sr_background_layer_id"] = "laundry_quad"
    laundry["sr_camera_space"] = False
    laundry["sr_reacts_to_pitch"] = True
    laundry["sr_floor_bridge"] = False
    laundry["sr_source_representation"] = "image-authored-alpha-world-space-quad"

    # Interrupt the paving with shallow masonry, drains and planting at
    # several depths. The central run stays open for the authored lane.
    fragments = (
        ("WEST", 5.0, -1.5, 2.8, .62),
        ("MID_WEST", 5.8, 2.0, 1.55, .46),
        ("MID_EAST", 6.0, 12.0, 1.75, .50),
        ("EAST", 4.8, 21.8, 2.3, .62),
    )
    for label, x, runtime_y, width, height in fragments:
        box(f"CORTICO_AUTHORED_EDGE_{label}",
            (x, by(runtime_y), height * .5), (.42, width, height), stone,
            foreground, "interrupted_edge_masonry")
        box(f"CORTICO_AUTHORED_DRAIN_{label}",
            (x + .24, by(runtime_y), .035), (.05, width * .78, .07), iron,
            foreground, "drainage_edge")
    for index, runtime_y in enumerate((-1.2, 16.0)):
        box(f"CORTICO_AUTHORED_PLANTER_{index}",
            (5.4, by(runtime_y), .32), (.75, 1.10, .64), old_stone,
            foreground, "interrupted_planting")
        box(f"CORTICO_AUTHORED_PLANT_{index}",
            (5.4, by(runtime_y), .90), (.24, .72, 1.05), plant,
            foreground, "interrupted_planting")
    for index, runtime_y in enumerate((5.0, 18.7)):
        box(f"CORTICO_AUTHORED_FRAME_POST_{index}",
            (6.25, by(runtime_y), .88), (.24, .26, 1.76), wood,
            foreground, "near_vertical_frame")

    # A shallow, visibly utilitarian workers' stair at its existing exit, plus
    # the padaria back-service canopy at its existing door.
    for index in range(6):
        box(f"CORTICO_AUTHORED_WORKERS_STEP_{index}",
            (10.4 + index * .52, by(20.125), .08 + index * .10),
            (.52, 1.85, .16 + index * .20), old_stone,
            architecture, "workers_stair")
    box("CORTICO_AUTHORED_PADARIA_BACK_CANOPY",
        (13.35, by(13.7448), 3.35), (1.0, 2.2, .18), roof,
        architecture, "padaria_service_canopy")
    for side in (-1, 1):
        box(f"CORTICO_AUTHORED_PADARIA_BACK_POST_{side}",
            (13.15, by(13.7448) + side * .85, 2.25), (.16, .16, 2.2), wood,
            architecture, "padaria_service_canopy")

    bpy.context.scene["sr_cortico_authored_detail_pass"] = (
        "subdivided thresholds, shared laundry, interrupted edges, "
        "workers stair and padaria service approach")
    bpy.context.scene["sr_cortico_authored_detail_version"] = 1
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    print("CORTICO DETAILS ADOPTED", blend)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    args = parser.parse_args()
    if not args.blend.is_file():
        raise SystemExit(f"source blend not found: {args.blend}")
    build(args.blend)


if __name__ == "__main__":
    if "--" in sys.argv:
        sys.argv = [sys.argv[0]] + sys.argv[sys.argv.index("--") + 1:]
    main()
