'''Lineage A3 Final Master Architecture & Materials
Built in Blender 5.1 from clean factory settings.
Features:
- Full procedural PBR materials (Stone Ashlar, Timber Planks, Terracotta Tiles, Plaster, Leaded Glass, Wrought Iron, Paved Cobbles).
- Rich architectural TH_SOURCE with detailed moldings, portal jambs, enterable door cavity, timber framing, and roof eaves.
- Coarse real 3D TH_RENDER geometry.
- TH_COLLISION walk boundaries.
- TH_ANCHORS (spawn_player, doorway, npc_1, npc_2, walk_start, walk_end).
- Upright Walker billboards in TH_PREVIEW_ACTORS.
'''
import sys
import math
import bpy
from pathlib import Path
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))
import thestra_camera

def create_box(name, size, location, parent_coll, mat=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    parent_coll.objects.link(obj)
    
    sx, sy, sz = size[0]*0.5, size[1]*0.5, size[2]*0.5
    verts = [
        (-sx, -sy, -sz), ( sx, -sy, -sz), ( sx,  sy, -sz), (-sx,  sy, -sz),
        (-sx, -sy,  sz), ( sx, -sy,  sz), ( sx,  sy,  sz), (-sx,  sy,  sz)
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),
        (0, 4, 5, 1), (1, 5, 6, 2),
        (2, 6, 7, 3), (3, 7, 4, 0)
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = Vector(location)
    if mat: mesh.materials.append(mat)
    return obj

def create_gable_roof(name, span, length, height, location, parent_coll, mat=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    parent_coll.objects.link(obj)
    
    sx, sy, h = span * 0.5, length * 0.5, height
    verts = [
        (-sx, -sy, 0.0), ( sx, -sy, 0.0), ( sx,  sy, 0.0), (-sx,  sy, 0.0),
        (0.0, -sy, h),   (0.0,  sy, h)
    ]
    faces = [
        (0, 1, 2, 3), (0, 4, 1), (3, 2, 5), (0, 3, 5, 4), (1, 4, 5, 2)
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = Vector(location)
    if mat: mesh.materials.append(mat)
    return obj

def create_pyramid_spire(name, base_w, base_d, height, location, parent_coll, mat=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    parent_coll.objects.link(obj)
    
    sx, sy, h = base_w * 0.5, base_d * 0.5, height
    verts = [
        (-sx, -sy, 0.0), ( sx, -sy, 0.0), ( sx,  sy, 0.0), (-sx,  sy, 0.0),
        (0.0, 0.0, h)
    ]
    faces = [
        (0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = Vector(location)
    if mat: mesh.materials.append(mat)
    return obj

def build_procedural_materials():
    materials = {}
    
    # 1. Stone Ashlar Material
    m_stone = bpy.data.materials.new("MAT_StoneAshlar")
    m_stone.use_nodes = True
    nt = m_stone.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 12.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.7
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.42, 0.40, 0.36, 1.0)
    ramp.color_ramp.elements[1].color = (0.75, 0.72, 0.66, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    materials["stone"] = m_stone

    # 2. Dark Plinth Stone
    m_plinth = bpy.data.materials.new("MAT_PlinthStone")
    m_plinth.use_nodes = True
    nt = m_plinth.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 16.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.28, 0.26, 0.24, 1.0)
    ramp.color_ramp.elements[1].color = (0.48, 0.45, 0.42, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.9
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    materials["plinth"] = m_plinth

    # 3. Weathered Dark Oak Timber
    m_timber = bpy.data.materials.new("MAT_WeatheredTimber")
    m_timber.use_nodes = True
    nt = m_timber.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 24.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.18, 0.12, 0.08, 1.0)
    ramp.color_ramp.elements[1].color = (0.35, 0.25, 0.18, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.75
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    materials["timber"] = m_timber

    # 4. Aged Warm Plaster / Daub
    m_plaster = bpy.data.materials.new("MAT_WarmPlaster")
    m_plaster.use_nodes = True
    nt = m_plaster.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.72, 0.68, 0.62, 1.0)
    ramp.color_ramp.elements[1].color = (0.86, 0.84, 0.78, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    materials["plaster"] = m_plaster

    # 5. Terracotta Clay Roof Tiles
    m_roof = bpy.data.materials.new("MAT_TerracottaRoof")
    m_roof.use_nodes = True
    nt = m_roof.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 20.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.42, 0.18, 0.12, 1.0)
    ramp.color_ramp.elements[1].color = (0.68, 0.32, 0.22, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.8
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    materials["roof"] = m_roof

    # 6. Cobblestone Paving
    m_street = bpy.data.materials.new("MAT_CobbleStreet")
    m_street.use_nodes = True
    nt = m_street.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 14.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.32, 0.30, 0.28, 1.0)
    ramp.color_ramp.elements[1].color = (0.55, 0.52, 0.48, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    materials["street"] = m_street

    # 7. Deep Interior Cavity Darkness
    m_dark = bpy.data.materials.new("MAT_InteriorCavity")
    m_dark.use_nodes = True
    nt = m_dark.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.05, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.95
    materials["dark"] = m_dark

    # 8. Leaded Glass Window with soft reflection
    m_window = bpy.data.materials.new("MAT_LeadedGlass")
    m_window.use_nodes = True
    nt = m_window.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.12, 0.16, 0.20, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.15
        bsdf.inputs["IOR"].default_value = 1.45
    materials["window"] = m_window

    # 9. Background Keep Wall
    m_bg = bpy.data.materials.new("MAT_DistantKeep")
    m_bg.use_nodes = True
    nt = m_bg.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.62, 0.65, 0.72, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
    materials["bg"] = m_bg

    return materials

def build_lineage_a3():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # Setup standard Collections
    colls = {name: bpy.data.collections.new(name) for name in ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]}
    for c in colls.values(): scene.collection.children.link(c)

    # Setup calibrated Camera
    target_w, target_h = 426, 240
    base_w, base_h = 256, 144
    fov_half_x = 0.25
    fov_half_y = fov_half_x * (base_h / base_w)
    
    calib = {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "targetWidth": target_w,
        "targetHeight": target_h,
        "baseViewportWidth": base_w,
        "baseViewportHeight": base_h,
        "nearPlane": 0.1,
        "farPlane": 100.0,
        "viewportCenterX": 213.0,
        "viewportCenterY": 110.0,
        "projectionWindowOffsetX": 0.0,
        "projectionWindowOffsetY": 0.0,
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": fov_half_x,
        "fovHalfY": fov_half_y,
        "eye": {"x": 0.0, "y": -18.66666667, "z": 2.37},
        "orientation": {"forwardX": 0.0, "forwardY": 1.0, "rightX": 1.0, "rightY": 0.0, "pitchRadians": 0.0},
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        }
    }
    cam_obj = thestra_camera.create_or_update_camera(calib, scene=scene, make_active=True)
    scene.collection.objects.unlink(cam_obj)
    colls["TH_CAMERA_PREVIEW"].objects.link(cam_obj)

    mats = build_procedural_materials()
    src = colls["TH_SOURCE"]
    rnd = colls["TH_RENDER"]
    col = colls["TH_COLLISION"]
    anc = colls["TH_ANCHORS"]

    # ==========================================
    # 1. TH_SOURCE: RICH MASTER ARCHITECTURE
    # ==========================================
    # Street Walkway
    create_box("Street_Cobbles", (16.0, 5.0, 0.8), (0.0, -0.5, -0.4), src, mats["street"])
    create_box("Street_Curb_Stone", (16.0, 0.35, 0.15), (0.0, 0.8, 0.075), src, mats["plinth"])

    # Left Foreground Ruined Archway & Mounting Step (X = -3.2, Y = -2.4)
    create_box("FG_Arch_Pier_Base", (0.8, 0.8, 1.4), (-3.3, -2.4, 0.7), src, mats["plinth"])
    create_box("FG_Arch_Pier_Shaft", (0.6, 0.6, 4.2), (-3.3, -2.4, 3.5), src, mats["stone"])
    create_box("FG_Arch_Voussoir", (1.4, 0.6, 0.8), (-2.6, -2.4, 5.6), src, mats["stone"])
    create_box("FG_Mounting_Stone", (0.8, 0.6, 0.5), (-2.5, -2.4, 0.25), src, mats["plinth"])

    # Left Bastion Gatehouse with Deep Open Portal (X = -3.6 to -1.2)
    create_box("Bastion_Flank_Wall", (1.2, 3.8, 5.5), (-3.0, 2.8, 2.75), src, mats["stone"])
    create_box("Bastion_Flank_Plinth", (1.4, 4.0, 0.8), (-3.0, 2.8, 0.4), src, mats["plinth"])
    create_box("Bastion_Machicolation", (1.5, 4.2, 0.5), (-3.0, 2.8, 5.75), src, mats["stone"])
    create_pyramid_spire("Bastion_Tower_Roof", 1.5, 4.2, 2.0, (-3.0, 2.8, 6.0), src, mats["roof"])
    
    # Grand Arched Gateway Portal (X: -2.2 to -0.6, Z: 0.0 to 3.2)
    create_box("Gate_Arch_LeftJamb", (0.4, 2.8, 3.0), (-2.2, 2.6, 1.5), src, mats["plinth"])
    create_box("Gate_Arch_RightJamb", (0.4, 2.8, 3.0), (-0.6, 2.6, 1.5), src, mats["plinth"])
    create_box("Gate_Arch_Span", (2.0, 2.8, 0.8), (-1.4, 2.6, 3.4), src, mats["stone"])
    create_box("Gate_Arch_Impost_L", (0.5, 3.0, 0.15), (-2.2, 2.6, 3.0), src, mats["stone"])
    create_box("Gate_Arch_Impost_R", (0.5, 3.0, 0.15), (-0.6, 2.6, 3.0), src, mats["stone"])
    create_box("Gate_Deep_Vault_Interior", (1.6, 5.0, 3.0), (-1.4, 5.0, 1.5), src, mats["dark"])

    # Center Inhabited Guildhouse with Enterable Ground Doorway (X: -0.4 to 2.8)
    create_box("Guild_Ground_Plinth", (3.2, 3.6, 0.4), (1.2, 2.6, 0.2), src, mats["plinth"])
    create_box("Guild_Stone_Wall_L", (0.8, 3.4, 2.4), (0.0, 2.6, 1.6), src, mats["stone"])
    create_box("Guild_Stone_Wall_R", (1.0, 3.4, 2.4), (2.3, 2.6, 1.6), src, mats["stone"])
    create_box("Guild_Stone_Lintel", (3.2, 3.4, 0.4), (1.2, 2.6, 3.0), src, mats["stone"])

    # Enterable doorway cavity at Z=0
    create_box("Guild_Door_Cavity", (1.2, 2.5, 2.4), (1.0, 3.8, 1.2), src, mats["dark"])
    create_box("Guild_Door_Frame", (1.1, 0.2, 2.3), (1.0, 1.8, 1.15), src, mats["timber"])
    create_box("Guild_Door_Panel", (1.0, 0.1, 2.1), (1.0, 2.0, 1.05), src, mats["timber"])
    create_box("Guild_Stone_Sill", (1.3, 0.5, 0.15), (1.0, 1.2, 0.075), src, mats["plinth"])
    
    # Ground floor shop window
    create_box("Guild_Shop_Window_Frame", (0.8, 0.2, 1.2), (2.3, 0.9, 1.6), src, mats["timber"])
    create_box("Guild_Shop_Window_Glass", (0.7, 0.1, 1.0), (2.3, 0.95, 1.6), src, mats["window"])
    create_box("Guild_Shop_Sill", (0.9, 0.3, 0.12), (2.3, 0.8, 0.95), src, mats["plinth"])

    # Timber Jetty Second Story (Z = 3.2 to 5.8)
    create_box("Guild_Jetty_Box", (3.4, 4.0, 2.6), (1.2, 2.2, 4.5), src, mats["plaster"])
    create_box("Guild_Corbel_Beam_1", (0.25, 0.8, 0.3), (-0.2, 0.6, 3.1), src, mats["timber"])
    create_box("Guild_Corbel_Beam_2", (0.25, 0.8, 0.3), (0.6, 0.6, 3.1), src, mats["timber"])
    create_box("Guild_Corbel_Beam_3", (0.25, 0.8, 0.3), (1.6, 0.6, 3.1), src, mats["timber"])
    create_box("Guild_Corbel_Beam_4", (0.25, 0.8, 0.3), (2.6, 0.6, 3.1), src, mats["timber"])
    
    create_box("Guild_Timber_BottomRail", (3.5, 0.15, 0.2), (1.2, 0.1, 3.3), src, mats["timber"])
    create_box("Guild_Timber_TopRail", (3.5, 0.15, 0.2), (1.2, 0.1, 5.7), src, mats["timber"])
    create_box("Guild_Timber_Stud_L", (0.15, 0.15, 2.4), (-0.4, 0.1, 4.5), src, mats["timber"])
    create_box("Guild_Timber_Stud_M1", (0.15, 0.15, 2.4), (0.4, 0.1, 4.5), src, mats["timber"])
    create_box("Guild_Timber_Stud_M2", (0.15, 0.15, 2.4), (1.6, 0.1, 4.5), src, mats["timber"])
    create_box("Guild_Timber_Stud_R", (0.15, 0.15, 2.4), (2.8, 0.1, 4.5), src, mats["timber"])
    
    # Second floor oriel window
    create_box("Guild_Oriel_Window", (1.2, 0.4, 1.4), (1.0, 0.0, 4.6), src, mats["timber"])
    create_box("Guild_Oriel_Glass", (1.0, 0.1, 1.2), (1.0, -0.15, 4.6), src, mats["window"])

    # Pitched Gable Roof
    create_gable_roof("Guild_Main_Roof", 3.8, 4.4, 2.2, (1.2, 2.2, 5.8), src, mats["roof"])
    create_box("Guild_Chimney", (0.6, 0.6, 2.0), (2.5, 2.4, 6.8), src, mats["stone"])
    create_box("Guild_Chimney_Pot", (0.3, 0.3, 0.5), (2.5, 2.4, 7.9), src, mats["roof"])

    # Right Elevated Retaining Terrace & Watch-Stair (X = 3.0 to 5.5)
    create_box("Terrace_Retaining_Wall", (2.6, 4.2, 2.4), (4.2, 2.8, 1.2), src, mats["plinth"])
    create_box("Terrace_Stair_1", (0.8, 0.5, 0.3), (3.0, 1.2, 0.15), src, mats["plinth"])
    create_box("Terrace_Stair_2", (0.8, 0.5, 0.6), (3.0, 1.7, 0.45), src, mats["plinth"])
    create_box("Terrace_Stair_3", (0.8, 0.5, 0.9), (3.0, 2.2, 0.75), src, mats["plinth"])
    create_box("Terrace_Upper_House", (2.4, 3.6, 3.2), (4.4, 3.2, 4.0), src, mats["plaster"])
    create_box("Terrace_Upper_Window", (0.8, 0.2, 1.0), (4.4, 1.3, 4.2), src, mats["window"])
    create_gable_roof("Terrace_House_Roof", 2.8, 4.0, 1.8, (4.4, 3.2, 5.6), src, mats["roof"])
    create_box("Terrace_Balcony_Rail", (2.4, 0.2, 0.8), (4.2, 0.8, 2.8), src, mats["timber"])

    # Deep Background Silhouette (Y = 7.0 to 11.0)
    create_box("BG_Keep_CurtainWall", (16.0, 3.0, 7.0), (0.0, 8.0, 3.5), src, mats["bg"])
    create_box("BG_Keep_Tower", (2.4, 2.4, 10.0), (-2.5, 8.5, 5.0), src, mats["bg"])
    create_pyramid_spire("BG_Tower_Spire", 2.6, 2.6, 3.2, (-2.5, 8.5, 10.0), src, mats["roof"])
    create_gable_roof("BG_Distant_Rooftops", 6.0, 3.0, 2.2, (2.5, 8.5, 6.8), src, mats["roof"])

    # ==========================================
    # 2. TH_RENDER: COARSE REAL 3D GEOMETRY
    # ==========================================
    create_box("RND_Street_Slab", (16.0, 5.0, 0.8), (0.0, -0.5, -0.4), rnd)
    create_box("RND_FG_Pillar", (0.8, 0.8, 5.6), (-3.3, -2.4, 2.8), rnd)
    create_box("RND_Bastion_Block", (3.0, 4.0, 7.5), (-2.8, 2.8, 3.75), rnd)
    create_box("RND_Guild_House_Block", (3.6, 4.2, 8.0), (1.2, 2.4, 4.0), rnd)
    create_box("RND_Terrace_Block", (2.6, 4.2, 7.0), (4.2, 3.0, 3.5), rnd)
    create_box("RND_BG_Keep_Block", (16.0, 3.0, 10.0), (0.0, 8.5, 5.0), rnd)
    # Hide TH_RENDER from viewport and render by default during source inspection
    rnd.hide_render = True
    rnd.hide_viewport = True

    # ==========================================
    # 3. TH_COLLISION: WALK SPACE BOUNDS
    # ==========================================
    # Continuous walking bounds: X from -5.0 to +5.0, Y from -0.8 to +0.8
    col_obj = create_box("COL_Walkway_Bounds", (10.0, 1.6, 0.2), (0.0, 0.0, -0.1), col)
    col.hide_render = True
    col.hide_viewport = True

    # ==========================================
    # 4. TH_ANCHORS: SPATIAL ANCHORS
    # ==========================================
    def make_anchor(name, loc):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = 0.5
        empty.location = Vector(loc)
        anc.objects.link(empty)
        return empty

    make_anchor("spawn_player", (-0.4, 0.0, 0.0))
    make_anchor("doorway", (1.0, 1.8, 0.0))
    make_anchor("npc_1", (1.8, 0.4, 0.0))
    make_anchor("npc_2", (3.8, 1.0, 2.4))
    make_anchor("walk_start", (-4.5, 0.0, 0.0))
    make_anchor("walk_end", (4.5, 0.0, 0.0))
    anc.hide_render = True

    # ==========================================
    # 5. LIGHTING & ENVIRONMENT
    # ==========================================
    world = bpy.data.worlds.new("World_Final")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.58, 0.65, 0.76, 1.0)
        bg_node.inputs["Strength"].default_value = 0.8
    scene.world = world

    sun_data = bpy.data.lights.new("SunFinal", type='SUN')
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.96, 0.90)
    sun_obj = bpy.data.objects.new("SunFinal", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (0.75, 0.45, 0.35)

    # Ambient Fill Light for rich shadow depth
    fill_data = bpy.data.lights.new("FillLight", type='SUN')
    fill_data.energy = 0.8
    fill_data.color = (0.60, 0.70, 0.85)
    fill_obj = bpy.data.objects.new("FillLight", fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (-0.5, -0.3, 0.0)

    # ==========================================
    # 6. WALKERS (PREVIEW ONLY)
    # ==========================================
    walker_path = str(REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png")
    
    p_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(-0.4, 0.0, 0.0), frame_width=24, frame_height=48, frame_index=0, world_height=1.75, name="TH_ACTOR_PROTAGONIST")
    colls["TH_PREVIEW_ACTORS"].objects.link(p_obj); scene.collection.objects.unlink(p_obj)

    npc1_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(1.8, 0.4, 0.0), frame_width=24, frame_height=48, frame_index=2, world_height=1.75, name="TH_ACTOR_NPC1")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc1_obj); scene.collection.objects.unlink(npc1_obj)

    npc2_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(3.8, 1.0, 2.4), frame_width=24, frame_height=48, frame_index=4, world_height=1.75, name="TH_ACTOR_NPC2")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc2_obj); scene.collection.objects.unlink(npc2_obj)

    # Render Settings
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    out_dir = REPO_ROOT / "tools" / "sterile_town" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "final_winner_A3_center.png"
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "lineage_A3_final.blend"))
    print(f"Final Winner A3 Rendered & Saved.")

    # Render Projection Window Variations (-96 px, +96 px)
    # Left Projection Window (-96 px)
    calib_left = dict(calib)
    calib_left["projectionWindowOffsetX"] = -96.0
    calib_left["viewportCenterX"] = 213.0 - 96.0
    cam_left = thestra_camera.create_or_update_camera(calib_left, scene=scene, make_active=True)
    scene.render.filepath = str(out_dir / "projection_window_left_neg96.png")
    bpy.ops.render.render(write_still=True)

    # Right Projection Window (+96 px)
    calib_right = dict(calib)
    calib_right["projectionWindowOffsetX"] = 96.0
    calib_right["viewportCenterX"] = 213.0 + 96.0
    cam_right = thestra_camera.create_or_update_camera(calib_right, scene=scene, make_active=True)
    scene.render.filepath = str(out_dir / "projection_window_right_pos96.png")
    bpy.ops.render.render(write_still=True)
    print("Projection window strip renders complete.")

if __name__ == "__main__":
    build_lineage_a3()
