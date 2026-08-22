"""Build the original Second Gate side-view town environment.

This builder deliberately keeps the authoring collections visible in the .blend
and leaves baking/export to town_environment_pipeline.py.  It is deterministic:
all geometry, procedural materials, camera calibration, and preview actors are
created from this file, while the only external visuals are the fresh CC0
material inputs and the repository's walker.png preview cutout.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WALKER_PATH = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
DEFAULT_CC0 = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_town" / "materials" / "cc0"


def col(name: str):
    import bpy
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def set_socket(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value


def rgb(hex_value: str):
    value = hex_value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def principled(name, color, roughness=0.8, metallic=0.0, emission=None, emission_strength=0.0):
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_socket(bsdf, "Base Color", (*color, 1.0))
    set_socket(bsdf, "Roughness", roughness)
    set_socket(bsdf, "Metallic", metallic)
    if emission is not None:
        if bsdf.inputs.get("Emission Color"):
            set_socket(bsdf, "Emission Color", (*emission, 1.0))
            set_socket(bsdf, "Emission Strength", emission_strength)
        elif bsdf.inputs.get("Emission"):
            set_socket(bsdf, "Emission", (*emission, 1.0))
    return mat


def procedural_material(name, base, accent, roughness=0.82, scale=4.0, metallic=0.0):
    """A compact generated material: broad color hierarchy plus fine relief."""
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 5.0
    tex.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*base, 1.0)
    ramp.color_ramp.elements[1].color = (*accent, 1.0)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.12
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    set_socket(bsdf, "Roughness", roughness)
    set_socket(bsdf, "Metallic", metallic)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def cobble_material(cc0_dir: Path):
    import bpy
    diff = cc0_dir / "cobblestone_pavement_diff_1k.jpg"
    disp = cc0_dir / "cobblestone_pavement_disp_1k.jpg"
    mat = bpy.data.materials.get("MAT_Cobbles_CC0") or bpy.data.materials.new("MAT_Cobbles_CC0")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    image = nodes.new("ShaderNodeTexImage")
    image.name = "CC0_Cobblestone_Albedo"
    image.image = bpy.data.images.load(str(diff), check_existing=True)
    image.image.colorspace_settings.name = "sRGB"
    image.interpolation = "Linear"
    height = nodes.new("ShaderNodeTexImage")
    height.name = "CC0_Cobblestone_Displacement"
    height.image = bpy.data.images.load(str(disp), check_existing=True)
    height.image.colorspace_settings.name = "Non-Color"
    height.interpolation = "Linear"
    bump = nodes.new("ShaderNodeBump")
    set_socket(bump, "Strength", 0.25)
    set_socket(bump, "Distance", 0.12)
    links.new(texcoord.outputs["Generated"], image.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], height.inputs["Vector"])
    links.new(image.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(height.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    set_socket(bsdf, "Roughness", 0.92)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat["sr_material_strategy"] = "cc0_input"
    mat["sr_material_source"] = "Poly Haven / cobblestone_pavement"
    mat["sr_material_license"] = "CC0"
    mat["sr_material_displacement_input"] = str(disp.relative_to(ROOT)).replace("\\", "/")
    return mat


def make_materials(cc0_dir: Path):
    mats = {
        "backdrop": procedural_material("MAT_Generated_Backdrop", rgb("#1b2834"), rgb("#354b58"), 0.98, 1.2),
        "stone": procedural_material("MAT_Generated_Stone", rgb("#5f6970"), rgb("#a19b86"), 0.94, 7.0),
        "plaster": procedural_material("MAT_Generated_Plaster", rgb("#8f8276"), rgb("#c4b8a0"), 0.9, 5.0),
        "wood": procedural_material("MAT_Generated_Timber", rgb("#30282a"), rgb("#74513e"), 0.86, 10.0),
        "roof": procedural_material("MAT_Generated_Roof", rgb("#303d4a"), rgb("#667684"), 0.9, 8.0),
        "iron": procedural_material("MAT_Generated_Iron", rgb("#151b20"), rgb("#485153"), 0.82, 14.0, 0.55),
        "cobbles": cobble_material(cc0_dir),
        "window": principled("MAT_Generated_Window", rgb("#172735"), 0.26, 0.15, rgb("#d8a25c"), 0.65),
        "lantern": principled("MAT_Generated_Lantern", rgb("#b66e32"), 0.36, 0.45, rgb("#ffc57a"), 3.5),
        "banner": principled("MAT_Generated_Banner", rgb("#6b2838"), 0.91),
        "dark": principled("MAT_Generated_DeepShadow", rgb("#11161b"), 0.98),
    }
    for key, mat in mats.items():
        mat["sr_material_strategy"] = mat.get("sr_material_strategy", "procedural_generated")
        if not mat.get("sr_material_source"):
            mat["sr_material_source"] = "build_second_gate_town.py"
        if not mat.get("sr_material_license"):
            mat["sr_material_license"] = "project-generated"
    return mats


def cube(name, location, scale, material, collection, bevel=0.0):
    import bpy
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Source_Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return move_to(obj, collection)


def prism(name, points, y, depth, material, collection, bevel=0.0):
    import bpy
    verts = [(x, y - depth * 0.5, z) for x, z in points]
    verts += [(x, y + depth * 0.5, z) for x, z in points]
    n = len(points)
    # The first face is the camera/source-facing side at y - depth/2.  Winding
    # it toward -Y is essential for selected-to-active baking; the previous
    # winding rendered fine but made the bake rays look away from TH_SOURCE.
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Source_Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return obj


def grid_panel(name, x0, x1, z0, z1, y, nx, nz, material, collection, displacement=False):
    import bpy
    verts = []
    for iz in range(nz + 1):
        z = z0 + (z1 - z0) * iz / nz
        for ix in range(nx + 1):
            x = x0 + (x1 - x0) * ix / nx
            verts.append((x, y, z))
    faces = []
    for iz in range(nz):
        for ix in range(nx):
            a = iz * (nx + 1) + ix
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    if displacement:
        texture = bpy.data.textures.new(name + "_RealSourceDisplacement", type="CLOUDS")
        texture.noise_scale = 0.34
        texture.noise_depth = 2
        mod = obj.modifiers.new("REAL_SOURCE_DISPLACEMENT", "DISPLACE")
        mod.texture = texture
        mod.texture_coords = "GLOBAL"
        mod.direction = "NORMAL"
        mod.strength = 0.18
        mod.mid_level = 0.5
        obj["sr_source_displacement"] = True
        obj["sr_displacement_strength_world"] = 0.18
        obj["sr_displacement_texture"] = texture.name
    return obj


def add_building(prefix, x, y, width, height, roof_rise, source_col, render_col, mats, style="stone", windows=2):
    facade_mat = mats[style]
    roof_mat = mats["roof"]
    points = [(x - width / 2, 0.0), (x - width / 2, height), (x + width / 2, height), (x + width / 2, 0.0)]
    prism("SRC_" + prefix + "_Facade", points, y, 1.05, facade_mat, source_col, 0.04)
    prism("RND_" + prefix + "_Facade", points, y, 1.05, facade_mat, render_col)
    roof_points = [(x - width / 2 - 0.28, height), (x, height + roof_rise), (x + width / 2 + 0.28, height)]
    prism("SRC_" + prefix + "_Roof", roof_points, y - 0.02, 1.3, roof_mat, source_col, 0.03)
    prism("RND_" + prefix + "_Roof", roof_points, y - 0.02, 1.3, roof_mat, render_col)
    window_w = min(0.64, (width - 0.7) / max(windows, 1))
    for i in range(windows):
        wx = x - width / 2 + 0.38 + i * ((width - 0.76) / max(windows - 1, 1))
        wz = min(height - 1.0, 2.15)
        cube("SRC_" + prefix + "_Window_%02d" % i, (wx, y - 0.59, wz), (window_w, 0.12, 0.72), mats["window"], source_col, 0.04)
        cube("SRC_" + prefix + "_WindowTrim_%02d" % i, (wx, y - 0.72, wz), (window_w + 0.11, 0.06, 0.84), mats["wood"], source_col, 0.02)
    door_w = min(0.95, width * 0.25)
    cube("SRC_" + prefix + "_Door", (x + width * 0.23, y - 0.58, 0.95), (door_w, 0.12, 1.0), mats["wood"], source_col, 0.04)
    cube("SRC_" + prefix + "_DoorLintel", (x + width * 0.23, y - 0.72, 2.03), (door_w + 0.16, 0.08, 0.12), mats["stone"], source_col, 0.02)
    # Thin roof ribs and one hanging banner are source-only details that bake
    # into the coarse roof/facade target.
    for rib in range(3):
        rx = x - width * 0.35 + rib * width * 0.35
        prism("SRC_" + prefix + "_RoofRib_%02d" % rib,
              [(rx - 0.035, height), (x, height + roof_rise + 0.035), (rx + 0.035, height)],
              y - 0.72, 0.06, mats["iron"], source_col)


def add_stair(prefix, x, y, steps, width, rise, run, source_col, render_col, mats):
    for i in range(steps):
        cx = x + (i - steps * 0.5) * run
        z = (i + 0.5) * rise
        cube("SRC_" + prefix + "_Step_%02d" % i, (cx, y, z - 0.04), (run * 0.52, 0.82, rise), mats["stone"], source_col, 0.03)
        cube("RND_" + prefix + "_Step_%02d" % i, (cx, y, z - 0.04), (run * 0.52, 0.82, rise), mats["stone"], render_col)


def add_foreground_frame(source_col, render_col, mats, variant):
    # Near-plane framing, intentionally in front of the walkable architecture.
    cube("SRC_Foreground_LeftPier", (-6.9, -1.45, 3.2), (0.62, 0.72, 6.4), mats["stone"], source_col, 0.1)
    cube("RND_Foreground_LeftPier", (-6.9, -1.45, 3.2), (0.62, 0.72, 6.4), mats["stone"], render_col)
    cube("SRC_Foreground_CapBeam", (-5.0, -1.45, 6.35), (3.35, 0.72, 0.56), mats["stone"], source_col, 0.1)
    cube("RND_Foreground_CapBeam", (-5.0, -1.45, 6.35), (3.35, 0.72, 0.56), mats["stone"], render_col)
    cube("SRC_Foreground_RightPier", (6.6, -1.1, 2.35), (0.44, 0.62, 4.7), mats["dark"], source_col, 0.07)
    cube("RND_Foreground_RightPier", (6.6, -1.1, 2.35), (0.44, 0.62, 4.7), mats["dark"], render_col)
    for i in range(5):
        x = -6.45 + i * 0.72
        cube("SRC_Foreground_Brick_%02d" % i, (x, -1.91, 5.96 + 0.04 * (i % 2)), (0.28, 0.08, 0.16), mats["iron"], source_col, 0.02)
    # A second near-plane horizontal line creates a readable overlap against
    # the rear roofs without turning the whole view into a flat silhouette.
    cube("SRC_Foreground_HangingBeam", (1.8, -0.85, 5.05), (4.8, 0.18, 0.16), mats["wood"], source_col, 0.04)
    cube("RND_Foreground_HangingBeam", (1.8, -0.85, 5.05), (4.8, 0.18, 0.16), mats["wood"], render_col)
    for i in range(4):
        x = -1.6 + i * 2.2
        cube("SRC_Foreground_Chain_%02d" % i, (x, -0.98, 4.45), (0.035, 0.06, 0.55), mats["iron"], source_col)
        cube("RND_Foreground_Chain_%02d" % i, (x, -0.98, 4.45), (0.035, 0.06, 0.55), mats["iron"], render_col)


def add_lineage_architecture(lineage, source_col, render_col, mats):
    if lineage == "A":
        add_building("A_LeftGate", -10.5, 4.8, 4.3, 5.8, 1.0, source_col, render_col, mats, "stone", 2)
        add_building("A_LeftHouse", -6.3, 3.9, 3.1, 4.2, 0.8, source_col, render_col, mats, "plaster", 2)
        add_building("A_CenterHall", -1.5, 4.4, 4.8, 4.8, 1.35, source_col, render_col, mats, "stone", 2)
        add_building("A_RightHouse", 4.0, 4.0, 4.4, 4.0, 0.9, source_col, render_col, mats, "wood", 2)
        add_building("A_RightTower", 9.3, 4.9, 3.8, 6.1, 1.1, source_col, render_col, mats, "stone", 2)
        add_stair("A_Causeway", -0.4, 1.7, 5, 4.8, 0.18, 0.7, source_col, render_col, mats)
    elif lineage == "B":
        add_building("B_LeftNarrow", -11.2, 4.5, 2.7, 6.5, 1.2, source_col, render_col, mats, "wood", 2)
        add_building("B_LeftEave", -8.0, 3.9, 3.8, 4.8, 1.55, source_col, render_col, mats, "plaster", 2)
        add_building("B_Crossing", -3.1, 4.4, 5.5, 4.2, 1.0, source_col, render_col, mats, "wood", 3)
        add_building("B_RightShop", 3.2, 3.8, 4.2, 5.0, 1.3, source_col, render_col, mats, "plaster", 2)
        add_building("B_RightTower", 8.7, 4.7, 3.0, 6.8, 1.25, source_col, render_col, mats, "wood", 2)
        cube("SRC_B_HighWalk", (0.2, 2.9, 4.85), (8.8, 0.32, 0.22), mats["wood"], source_col, 0.06)
        cube("RND_B_HighWalk", (0.2, 2.9, 4.85), (8.8, 0.32, 0.22), mats["wood"], render_col)
        for i in range(7):
            x = -6.2 + i * 2.0
            cube("SRC_B_HighWalkPost_%02d" % i, (x, 2.9, 2.6), (0.16, 0.25, 2.25), mats["wood"], source_col, 0.03)
            cube("RND_B_HighWalkPost_%02d" % i, (x, 2.9, 2.6), (0.16, 0.25, 2.25), mats["wood"], render_col)
    elif lineage == "C":
        add_building("C_LeftCloister", -10.4, 4.8, 5.0, 5.4, 0.85, source_col, render_col, mats, "plaster", 3)
        add_building("C_LeftKeep", -5.2, 5.0, 2.5, 7.2, 1.0, source_col, render_col, mats, "stone", 2)
        add_building("C_CentralShrine", 0.0, 4.4, 4.2, 4.8, 1.45, source_col, render_col, mats, "stone", 2)
        passage = [(-0.86, 0.0), (-0.86, 2.2), (-0.62, 2.68), (0.0, 2.98), (0.62, 2.68), (0.86, 2.2), (0.86, 0.0)]
        prism("SRC_CentralShrine_Passage", passage, 3.78, 0.18, mats["dark"], source_col, 0.03)
        prism("RND_CentralShrine_Passage", passage, 3.78, 0.18, mats["dark"], render_col)
        cube("SRC_CentralShrine_PassageLeft", (-1.02, 3.68, 1.48), (0.16, 0.14, 1.48), mats["stone"], source_col, 0.03)
        cube("SRC_CentralShrine_PassageRight", (1.02, 3.68, 1.48), (0.16, 0.14, 1.48), mats["stone"], source_col, 0.03)
        cube("RND_CentralShrine_PassageLeft", (-1.02, 3.68, 1.48), (0.16, 0.14, 1.48), mats["stone"], render_col)
        cube("RND_CentralShrine_PassageRight", (1.02, 3.68, 1.48), (0.16, 0.14, 1.48), mats["stone"], render_col)
        add_building("C_RightTerrace", 5.0, 4.0, 4.2, 3.8, 0.7, source_col, render_col, mats, "plaster", 2)
        add_building("C_BellTower", 10.0, 5.2, 3.3, 7.7, 1.35, source_col, render_col, mats, "stone", 2)
        add_stair("C_TerraceSteps", 2.2, 1.6, 6, 4.5, 0.16, 0.68, source_col, render_col, mats)
        cube("SRC_C_ShrineBridge", (1.8, 2.8, 3.0), (4.2, 0.24, 0.18), mats["stone"], source_col, 0.05)
        cube("RND_C_ShrineBridge", (1.8, 2.8, 3.0), (4.2, 0.24, 0.18), mats["stone"], render_col)


def add_common_geometry(source_col, render_col, collision_col, mats, lineage):
    # Continuous walking band: its x-span deliberately exceeds all three
    # projection windows and has no seams at -96/0/+96.
    cube("SRC_WalkBand", (0.0, 0.55, -0.22), (18.0, 2.6, 0.44), mats["cobbles"], source_col, 0.04)
    cube("RND_WalkBand", (0.0, 0.55, -0.22), (18.0, 2.6, 0.44), mats["cobbles"], render_col)
    # Major source displacement field: the render target is a coarse facade
    # while this dense source panel carries true evaluated relief.
    # Keep the displaced field behind the authored town row.  It is still a
    # major visible surface, but it must not flatten the mid-plane buildings.
    grid_panel("SRC_Displaced_Masonry_Field", -15.5, 15.5, 0.0, 5.1, 6.35, 64, 24, mats["stone"], source_col, True)
    grid_panel("RND_Masonry_Field", -15.5, 15.5, 0.0, 5.1, 6.35, 8, 3, mats["stone"], render_col, False)
    add_lineage_architecture(lineage, source_col, render_col, mats)
    add_foreground_frame(source_col, render_col, mats, lineage)
    # Sign/lantern landmarks make the continuous street legible at each pan.
    for x, y, z in [(-8.5, 1.9, 2.9), (3.6, 1.8, 2.8), (11.8, 2.0, 3.2)]:
        cube("SRC_Lantern_Post_%s" % str(x).replace("-", "m").replace(".", "_"), (x, y, 1.5), (0.08, 0.08, 1.5), mats["iron"], source_col, 0.03)
        cube("RND_Lantern_Post_%s" % str(x).replace("-", "m").replace(".", "_"), (x, y, 1.5), (0.08, 0.08, 1.5), mats["iron"], render_col)
        cube("SRC_Lantern_%s" % str(x).replace("-", "m").replace(".", "_"), (x, y - 0.08, 3.08 if z > 3 else 2.82), (0.22, 0.18, 0.24), mats["lantern"], source_col, 0.05)
        cube("RND_Lantern_%s" % str(x).replace("-", "m").replace(".", "_"), (x, y - 0.08, 3.08 if z > 3 else 2.82), (0.22, 0.18, 0.24), mats["lantern"], render_col)
    # Keep the coarse target just behind the detailed source so Blender's
    # selected-to-active rays have a real source/target interval. This is a
    # bake-space separation only; the authored silhouette stays aligned.
    for obj in render_col.objects:
        if obj.type == "MESH":
            obj.location.y += 0.12
    # Collision is intentionally simpler than the render mesh.
    cube("COL_ContinuousGround", (0.0, 0.55, -0.27), (18.0, 2.6, 0.27), None, collision_col)
    cube("COL_LeftPier", (-6.9, -1.45, 3.2), (0.68, 0.75, 3.2), None, collision_col)
    cube("COL_RightPier", (6.6, -1.1, 2.35), (0.5, 0.68, 2.35), None, collision_col)
    cube("COL_StairCore", (2.2, 1.6, 0.48), (2.5, 0.9, 0.48), None, collision_col)


def make_actor_material():
    import bpy
    mat = bpy.data.materials.get("MAT_PREVIEW_Walker_Nearest") or bpy.data.materials.new("MAT_PREVIEW_Walker_Nearest")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(WALKER_PATH), check_existing=True)
    tex.interpolation = "Closest"
    tex.extension = "CLIP"
    tex.image["sr_filter"] = "nearest"
    tex.image["sr_source"] = str(WALKER_PATH.relative_to(ROOT)).replace("\\", "/")
    sep = nodes.new("ShaderNodeRGBToBW")
    alpha = nodes.new("ShaderNodeMath")
    alpha.operation = "GREATER_THAN"
    alpha.inputs[1].default_value = 0.035
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Val"], alpha.inputs[0])
    links.new(tex.outputs["Color"], bsdf.inputs["Alpha"])
    links.new(alpha.outputs[0], bsdf.inputs["Alpha"])
    set_socket(bsdf, "Roughness", 0.9)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    try:
        mat.surface_render_method = "DITHERED"
    except Exception:
        pass
    mat["sr_preview_only"] = True
    mat["sr_filter"] = "nearest"
    return mat


def actor_quad(name, x, y, z, frame, collection, material):
    import bpy
    w, h = 0.95, 1.62
    verts = [(x - w / 2, y, z), (x + w / 2, y, z), (x + w / 2, y, z + h), (x - w / 2, y, z + h)]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    uv = mesh.uv_layers.new(name="UVMap")
    u0, u1 = frame / 3.0, (frame + 1) / 3.0
    values = [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]
    for loop in mesh.loops:
        uv.data[loop.index].uv = values[loop.vertex_index]
    mesh.materials.append(material)
    obj["sr_preview_only"] = True
    obj["sr_feet_anchor_world"] = [round(x, 4), round(y, 4), round(z, 4)]
    obj["sr_frame"] = frame
    return obj


def anchor(name, loc, yaw, collection, kind="actor"):
    import bpy
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "ARROWS"
    empty.empty_display_size = 0.44
    empty.location = loc
    empty.rotation_euler[2] = math.radians(yaw)
    empty["sr_anchor_kind"] = kind
    empty["sr_feet_anchor"] = kind == "actor"
    collection.objects.link(empty)
    return empty


def setup_camera(camera_col):
    import bpy
    data = bpy.data.cameras.new("TH_Camera_43_27mm")
    camera = bpy.data.objects.new("TH_CAMERA_PREVIEW_FIXED_EYE", data)
    camera.location = (0.0, -18.0, 3.55)
    camera.rotation_euler = (math.pi / 2, 0.0, 0.0)
    data.type = "PERSP"
    data.lens = 43.27
    data.sensor_width = 36.0
    data.clip_start = 0.1
    data.clip_end = 60.0
    data.dof.use_dof = False
    camera["sr_camera_lens_mm"] = 43.27
    camera["sr_camera_level_side_view"] = True
    camera["sr_tracking_mode"] = "projection_window_translate_x_only"
    camera["sr_native_resolution"] = "426x240"
    camera["sr_projection_offsets_px"] = json.dumps([-96, 0, 96])
    camera_col.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def setup_lighting(source_col):
    import bpy
    world = bpy.context.scene.world or bpy.data.worlds.new("SecondGateWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    set_socket(bg, "Color", (*rgb("#101923"), 1.0))
    set_socket(bg, "Strength", 0.28)
    def light(name, kind, loc, energy, color, size=4.0):
        bpy.ops.object.light_add(type=kind, location=loc)
        obj = bpy.context.active_object
        obj.name = name
        obj.data.energy = energy
        obj.data.color = color
        if kind == "AREA":
            obj.data.shape = "RECTANGLE"
            obj.data.size = size
            obj.data.size_y = size * 0.6
            obj.rotation_euler = ((math.pi / 2), 0, 0)
        move_to(obj, source_col)
        return obj
    light("SRC_Warm_Side_Key", "AREA", (-7.0, -7.0, 9.0), 900.0, rgb("#e7b077"), 7.0)
    light("SRC_Cool_Rim", "AREA", (10.0, 4.0, 8.0), 1100.0, rgb("#7c9eb5"), 8.0)
    light("SRC_Fill", "AREA", (0.0, -2.0, 2.0), 380.0, rgb("#c5d0d7"), 5.0)
    for x in (-8.5, 3.6, 11.8):
        light("SRC_Lantern_Point_%s" % str(x).replace("-", "m").replace(".", "_"), "POINT", (x, 0.4, 3.0), 125.0, rgb("#ffb05a"), 0.2)


def clayify(source_col):
    import bpy
    palettes = {
        "back": principled("CLAY_Back", rgb("#33414b"), 1.0),
        "dark": principled("CLAY_Deep", rgb("#1a2027"), 1.0),
        "roof": principled("CLAY_Roof", rgb("#5a6671"), 1.0),
        "stone": principled("CLAY_Stone", rgb("#9a9385"), 1.0),
        "wood": principled("CLAY_Wood", rgb("#745b4d"), 1.0),
    }
    for obj in source_col.objects:
        if obj.type != "MESH":
            continue
        name = obj.name.lower()
        mat = palettes["dark"] if "foreground" in name else palettes["stone"]
        if "roof" in name or "beam" in name or "rib" in name:
            mat = palettes["roof"]
        if "window" in name or "door" in name:
            mat = palettes["dark"]
        if "passage" in name:
            mat = palettes["dark"]
        if "walkband" in name:
            mat = palettes["wood"]
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def configure_render(scene, path, width=426, height=240):
    # The installed Blender 5.1 build keeps the legacy enum name for Eevee.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def hide_collection(collection, hidden):
    collection.hide_render = hidden
    for obj in collection.objects:
        obj.hide_render = hidden


def unwrap_render_collection(render_col):
    import bpy
    render_meshes = [obj for obj in render_col.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in render_meshes:
        obj.select_set(True)
    if not render_meshes:
        return
    bpy.context.view_layer.objects.active = render_meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.035)
    bpy.ops.object.mode_set(mode="OBJECT")
    for obj in render_meshes:
        obj["sr_uv_unwrap"] = "smart_project"
        obj["sr_uv_island_margin"] = 0.035


def build_scene(lineage: str, out_dir: Path, stage: str):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    names = ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]
    cols = {name: col(name) for name in names}
    cc0_dir = out_dir / "materials" / "cc0"
    if not cc0_dir.is_dir():
        cc0_dir = DEFAULT_CC0
    mats = make_materials(cc0_dir)
    add_common_geometry(cols["TH_SOURCE"], cols["TH_RENDER"], cols["TH_COLLISION"], mats, lineage)
    unwrap_render_collection(cols["TH_RENDER"])
    setup_lighting(cols["TH_SOURCE"])
    camera = setup_camera(cols["TH_CAMERA_PREVIEW"])
    actor_mat = make_actor_material()
    actor_quad("ACTOR_Walker_Left", -3.4, -0.78, 0.0, 0, cols["TH_PREVIEW_ACTORS"], actor_mat)
    actor_quad("ACTOR_Walker_Center", 0.3, -0.76, 0.0, 1, cols["TH_PREVIEW_ACTORS"], actor_mat)
    actor_quad("ACTOR_Walker_Right", 4.8, -0.76, 0.0, 2, cols["TH_PREVIEW_ACTORS"], actor_mat)
    anchor("spawn_player", (-3.4, -0.72, 0.0), 0.0, cols["TH_ANCHORS"], "actor")
    anchor("street_center", (0.0, 0.7, 0.0), 0.0, cols["TH_ANCHORS"], "camera_focus")
    anchor("market_interaction", (3.6, 1.6, 2.8), 180.0, cols["TH_ANCHORS"], "interaction")
    anchor("bell_tower_vfx", (10.0, 5.0, 6.8), 90.0, cols["TH_ANCHORS"], "vfx")
    anchor("left_arch_occlusion", (-6.9, -1.45, 3.0), 0.0, cols["TH_ANCHORS"], "camera_focus")
    # Preview-only guide: a thin baseline and three projection-window markers.
    cube("GUIDE_Baseline", (0.0, -2.4, 0.02), (18.0, 0.04, 0.04), principled("GUIDE_Mat", rgb("#d4a96a"), 1.0), cols["TH_PREVIEW_ONLY"])
    for px in (-96, 0, 96):
        x = px * (15.1 / 426.0)
        cube("GUIDE_Projection_%s" % ("m96" if px < 0 else "p96" if px > 0 else "zero"), (x, -2.35, 1.0), (0.02, 0.03, 1.0), principled("GUIDE_Marker_%s" % px, rgb("#d4a96a"), 1.0), cols["TH_PREVIEW_ONLY"])
    # Render source proof with source geometry only; render target is hidden.
    hide_collection(cols["TH_RENDER"], True)
    hide_collection(cols["TH_COLLISION"], True)
    hide_collection(cols["TH_PREVIEW_ACTORS"], True)
    hide_collection(cols["TH_PREVIEW_ONLY"], True)
    hide_collection(cols["TH_ANCHORS"], True)
    configure_render(scene, out_dir / "source_proof.png")
    if stage == "clay":
        clayify(cols["TH_SOURCE"])
        configure_render(scene, out_dir / "clay.png")
    scene.render.filepath = str(out_dir / ("clay.png" if stage == "clay" else "source_proof.png"))
    out_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    # Restore a bake-ready scene and save the authoring source.
    hide_collection(cols["TH_RENDER"], False)
    hide_collection(cols["TH_COLLISION"], False)
    hide_collection(cols["TH_PREVIEW_ACTORS"], False)
    hide_collection(cols["TH_PREVIEW_ONLY"], False)
    hide_collection(cols["TH_ANCHORS"], False)
    hide_collection(cols["TH_CAMERA_PREVIEW"], False)
    scene["sr_environment_id"] = "second_gate_lantern_cleft"
    scene["sr_lineage"] = lineage
    scene["sr_contract"] = "TH_SOURCE -> UV-baked TH_RENDER"
    scene["sr_preview_resolution"] = "426x240"
    scene["sr_camera_lens_mm"] = 43.27
    scene["sr_projection_window_offsets_px"] = "-96,0,96"
    scene["sr_source_displacement_required"] = True
    blend_path = out_dir / ("lineage_%s.blend" % lineage.lower())
    if stage != "clay":
        blend_path = out_dir / "second_gate_lantern_cleft.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(json.dumps({"lineage": lineage, "stage": stage, "blend": str(blend_path), "clay": str(out_dir / "clay.png") if stage == "clay" else None}, sort_keys=True))


def main():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--lineage", choices=["A", "B", "C"], required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=["clay", "full"], default="clay")
    args = parser.parse_args(values)
    build_scene(args.lineage, args.out_dir.resolve(), args.stage)


if __name__ == "__main__":
    main()
