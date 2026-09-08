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
    "projects/hichaukitoden-game/assets/materials/cortico_laundry_quad_v2.png")


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


def ranked_box(name, location, size, mat, target, role, depth_rank):
    """Create an exported source mesh with an explicit exterior depth rank."""
    obj = box(name, location, size, mat, target, role)
    obj["sr_depth_rank"] = depth_rank
    return obj


def foliage_cluster(name, x, runtime_y, z, scale, mat, target, role,
                    depth_rank="BACKGROUND"):
    """Use a few faceted foliage masses instead of a continuous green wall."""
    objects = []
    for index, (dy, dz, sx) in enumerate((
            (-.42, 0.0, .78), (0.0, .18, 1.0), (.42, -.04, .72))):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1,
            radius=1.0,
            location=(x, by(runtime_y + dy * scale), z + dz * scale))
        obj = bpy.context.object
        obj.name = f"{name}_{index}"
        obj.scale = (scale * sx, scale * .58, scale * .82)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        link_only(obj, target)
        obj.data.materials.append(mat)
        tag(obj, role)
        obj["sr_depth_rank"] = depth_rank
        objects.append(obj)
    return objects


def face(name, x, y0, y1, z0, z1, mat, target, role):
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)],
                     [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    mesh.materials.append(mat)
    return tag(obj, role)


def edge_strip(name, x, runtime_y0, runtime_y1, depth, top_profile,
               body_mat, top_mat, target, role):
    """Build one connected, irregular low edge that can leave the frame."""
    if len(top_profile) < 3:
        raise ValueError("edge strip needs at least three profile points")
    step = (runtime_y1 - runtime_y0) / (len(top_profile) - 1)
    ys = [by(runtime_y0 + step * index)
          for index in range(len(top_profile))]
    vertices = []
    for y, top in zip(ys, top_profile):
        vertices.extend(((x, y, 0.0), (x + depth, y, 0.0),
                         (x, y, top), (x + depth, y, top)))
    faces = []
    material_indices = []
    for index in range(len(top_profile) - 1):
        a = index * 4
        b = (index + 1) * 4
        faces.extend(((a, b, b + 2, a + 2),
                      (a + 1, a + 3, b + 3, b + 1),
                      (a + 2, b + 2, b + 3, a + 3)))
        material_indices.extend((0, 0, 1))
    faces.extend(((0, 2, 3, 1),
                  ((len(top_profile) - 1) * 4,
                   (len(top_profile) - 1) * 4 + 1,
                   (len(top_profile) - 1) * 4 + 3,
                   (len(top_profile) - 1) * 4 + 2)))
    material_indices.extend((0, 0))
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(body_mat)
    mesh.materials.append(top_mat)
    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
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

    # Near rank: four connected edge fragments, intentionally longer than a
    # proof frame. They frame corners/bottom margins and carry a soil cap, so
    # the eye reads a rooted courtyard edge rather than floating blocks. The
    # centre opening from runtime Y 8.8..15.2 stays clear for traversal.
    near_strips = (
        ("WEST_FRAME", 4.85, -8.5, -2.0, .72,
         (.28, .38, .32, .48, .35, .43)),
        ("CENTRE_LEFT", 5.10, 8.3, 11.0, .58,
         (.22, .30, .25, .36, .27)),
        ("CENTRE_RIGHT", 5.30, 13.0, 15.8, .58,
         (.24, .33, .27, .39, .29)),
        ("EAST_FRAME", 4.85, 24.0, 31.6, .76,
         (.30, .40, .34, .46, .38, .31)),
    )
    for label, x, runtime_y0, runtime_y1, depth, profile in near_strips:
        edge = edge_strip(f"CORTICO_AUTHORED_NEAR_EDGE_{label}", x,
                          runtime_y0, runtime_y1, depth, profile, old_stone,
                          stone, foreground, "near_connected_masonry_soil_edge")
        edge["sr_depth_rank"] = "NEAR"
    for index, runtime_y in enumerate((-1.5, 28.0)):
        foliage_cluster(f"CORTICO_AUTHORED_NEAR_FOLIAGE_{index}", 5.0,
                        runtime_y, .72, .62, plant, foreground,
                        "near_fragmented_foliage", "NEAR")

    # Background rank: occupied, staggered household roofs and terraces at
    # both ends of the town. Each module is deliberately separated so sky
    # gaps survive, while the west/east camera views no longer read as a lone
    # blank wall. These are source geometry, not a replacement for the
    # exported pitch-reactive background cards.
    background_modules = (
        ("WEST_REAR_BAND", 21.4, -13.0, 5.8, 5.0, old_stone),
        ("WEST_FAR_TERRACE", 28.8, -7.0, 5.0, 5.6, roof),
        ("WEST_OPEN_EDGE", 32.0, -1.2, 3.8, 4.8, whitewash),
        ("EAST_REAR_BAND", 21.4, 30.0, 5.8, 4.9, whitewash),
        ("EAST_FAR_TERRACE", 28.8, 36.0, 5.2, 5.7, roof),
        ("EAST_OPEN_EDGE", 32.0, 42.0, 4.1, 5.0, old_stone),
        ("CENTRE_TERRACE", 25.4, 12.0, 3.8, 3.6, old_stone),
    )
    for label, x, runtime_y, width, height, wall_mat in background_modules:
        ranked_box(f"CORTICO_AUTHORED_BACKGROUND_WALL_{label}",
                   (x, by(runtime_y), height * .5),
                   (2.7, width, height), wall_mat, architecture,
                   "staggered_background_household", "BACKGROUND")
        ranked_box(f"CORTICO_AUTHORED_BACKGROUND_ROOF_{label}",
                   (x - .35, by(runtime_y), height + .22),
                   (3.5, width + .35, .34), roof, architecture,
                   "staggered_background_roofline", "BACKGROUND")
        ranked_box(f"CORTICO_AUTHORED_BACKGROUND_DOOR_{label}",
                   (x - 1.38, by(runtime_y), 1.05),
                   (.10, min(1.1, width * .30), 2.1), wood, architecture,
                   "background_household_threshold", "BACKGROUND")
    for index, (x, runtime_y, scale) in enumerate(
            ((22.2, -12.0, 1.65), (29.8, -6.0, 1.35),
             (22.2, 32.0, 1.60), (30.8, 38.5, 1.65),
             (27.0, 7.0, 1.05))):
        foliage_cluster(f"CORTICO_AUTHORED_BACKGROUND_TREE_{index}", x,
                        runtime_y, 4.15, scale, plant, architecture,
                        "staggered_background_vegetation", "BACKGROUND")

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
        "subdivided thresholds, shared laundry, interrupted near edges, "
        "staggered background households, vegetation, workers stair and "
        "padaria service approach")
    bpy.context.scene["sr_cortico_authored_detail_version"] = 2
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
