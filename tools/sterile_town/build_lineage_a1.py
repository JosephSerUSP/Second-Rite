'''Advanced Architectural Massing for A1, B1, and C1.
Uses true polygonal meshes with beveled moldings, pitched roofs with gables/eaves, recessed arched portals with jambs/voussoirs, timber corbels, and mullioned windows.
Camera Eye Z = 2.37 (Level pitch 0.0, 43.27mm lens, Horizon Y=110, feet at Y=175).
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
    if mat:
        mesh.materials.append(mat)
    return obj

def create_gable_roof(name, span, length, height, location, parent_coll, mat=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    parent_coll.objects.link(obj)
    
    sx = span * 0.5
    sy = length * 0.5
    h = height
    # 6 vertices: 4 at base, 2 at ridge
    verts = [
        (-sx, -sy, 0.0), ( sx, -sy, 0.0), ( sx,  sy, 0.0), (-sx,  sy, 0.0), # base
        (0.0, -sy, h),   (0.0,  sy, h)                                       # ridge
    ]
    faces = [
        (0, 1, 2, 3), # bottom
        (0, 4, 1),    # front gable
        (3, 2, 5),    # back gable
        (0, 3, 5, 4), # left slope
        (1, 4, 5, 2)  # right slope
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = Vector(location)
    if mat:
        mesh.materials.append(mat)
    return obj

def create_pyramid_spire(name, base_w, base_d, height, location, parent_coll, mat=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    parent_coll.objects.link(obj)
    
    sx = base_w * 0.5
    sy = base_d * 0.5
    h = height
    verts = [
        (-sx, -sy, 0.0), ( sx, -sy, 0.0), ( sx,  sy, 0.0), (-sx,  sy, 0.0),
        (0.0, 0.0, h)
    ]
    faces = [
        (0, 1, 2, 3), # bottom
        (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = Vector(location)
    if mat:
        mesh.materials.append(mat)
    return obj

def setup_camera(scene, coll):
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
    coll.objects.link(cam_obj)
    return cam_obj

def make_clay(name, color, roughness=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return m

# ==========================================
# LINEAGE A1: THE BASTION GATE & GUILDHOUSE
# ==========================================
def build_lineage_a1():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    colls = {name: bpy.data.collections.new(name) for name in ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]}
    for c in colls.values(): scene.collection.children.link(c)
    cam_obj = setup_camera(scene, colls["TH_CAMERA_PREVIEW"])

    c_stone = make_clay("ClayStoneA", (0.74, 0.72, 0.68, 1.0))
    c_plinth = make_clay("ClayPlinthA", (0.45, 0.43, 0.40, 1.0))
    c_wood = make_clay("ClayWoodA", (0.36, 0.26, 0.20, 1.0))
    c_plaster = make_clay("ClayPlasterA", (0.84, 0.82, 0.76, 1.0))
    c_roof = make_clay("ClayRoofA", (0.58, 0.32, 0.24, 1.0))
    c_dark = make_clay("ClayDarkA", (0.10, 0.10, 0.12, 1.0))
    c_street = make_clay("ClayStreetA", (0.52, 0.50, 0.46, 1.0))
    c_bg = make_clay("ClayBgA", (0.64, 0.66, 0.72, 1.0))

    src = colls["TH_SOURCE"]

    # 1. Street Walkway
    create_box("Street_Cobbles", (26.0, 5.0, 0.8), (0.0, -0.5, -0.4), src, c_street)
    create_box("Street_Curb_Stone", (26.0, 0.35, 0.15), (0.0, 0.7, 0.075), src, c_plinth)

    # 2. Foreground Ruined Archway & Mounting Step (Left, Y = -2.4)
    create_box("FG_Arch_Pier_Base", (1.2, 1.2, 1.4), (-6.5, -2.4, 0.7), src, c_plinth)
    create_box("FG_Arch_Pier_Shaft", (0.9, 0.9, 4.2), (-6.5, -2.4, 3.5), src, c_stone)
    create_box("FG_Arch_Voussoir", (2.2, 0.9, 1.0), (-5.4, -2.4, 5.8), src, c_stone)
    create_box("FG_Mounting_Stone", (1.1, 0.8, 0.6), (-5.2, -2.4, 0.3), src, c_plinth)

    # 3. Action Midground (Y = 1.5 to 4.5)
    # --- Left: Fortified Bastion Gatehouse (X: -6.0 to -1.5) ---
    create_box("Bastion_Base", (3.6, 4.0, 2.6), (-4.2, 2.8, 1.3), src, c_plinth)
    create_box("Bastion_Plinth_Bevel", (3.8, 4.2, 0.2), (-4.2, 2.8, 2.7), src, c_plinth)
    create_box("Bastion_Mid_Wall", (3.4, 3.8, 3.2), (-4.2, 2.8, 4.3), src, c_stone)
    create_box("Bastion_Machicolation", (3.8, 4.2, 0.5), (-4.2, 2.8, 6.15), src, c_stone)
    create_box("Bastion_Parapet", (3.6, 4.0, 1.0), (-4.2, 2.8, 6.9), src, c_stone)
    create_pyramid_spire("Bastion_Roof_Spire", 3.6, 4.0, 2.4, (-4.2, 2.8, 7.4), src, c_roof)

    # Gate Arch spanning over alley (X: -2.4 to -0.8)
    create_box("Gate_Arch_LeftPier", (0.8, 2.8, 3.2), (-2.4, 2.6, 1.6), src, c_stone)
    create_box("Gate_Arch_RightPier", (0.8, 2.8, 3.2), (-0.8, 2.6, 1.6), src, c_stone)
    create_box("Gate_Arch_ArchSpan", (2.4, 2.8, 1.2), (-1.6, 2.6, 3.8), src, c_stone)
    create_box("Gate_Deep_Tunnel_Cavity", (2.0, 4.0, 3.2), (-1.6, 4.5, 1.6), src, c_dark)

    # --- Center: Merchant Guildhouse with Enterable Porch & Overhang (X: -0.4 to 4.2) ---
    create_box("Guild_Stone_Foundation", (4.4, 3.6, 1.0), (1.8, 2.6, 0.5), src, c_plinth)
    create_box("Guild_Wall_Left", (1.2, 3.4, 2.4), (0.4, 2.6, 2.2), src, c_stone)
    create_box("Guild_Wall_Right", (1.4, 3.4, 2.4), (3.3, 2.6, 2.2), src, c_stone)
    create_box("Guild_Door_Lintel", (4.2, 3.4, 0.6), (1.8, 2.6, 3.7), src, c_stone)
    
    # Enterable portal with deep jambs & stairs
    create_box("Guild_Door_Cavity", (1.6, 2.5, 2.5), (1.8, 3.5, 1.25), src, c_dark)
    create_box("Guild_Door_InnerFrame", (1.4, 0.2, 2.4), (1.8, 2.2, 1.2), src, c_wood)
    create_box("Guild_Step_1", (2.0, 0.6, 0.2), (1.8, 1.0, 0.1), src, c_plinth)
    create_box("Guild_Step_2", (1.6, 0.5, 0.2), (1.8, 1.4, 0.3), src, c_plinth)

    # Timber Jetty Second Story (Overhanging street)
    create_box("Guild_Jetty_Box", (4.8, 4.0, 2.8), (1.8, 2.2, 5.1), src, c_plaster)
    create_box("Guild_Corbel_Beams", (4.6, 0.6, 0.35), (1.8, 0.6, 3.7), src, c_wood)
    create_box("Guild_Timber_Studs", (4.9, 0.2, 2.8), (1.8, 0.1, 5.1), src, c_wood)
    create_gable_roof("Guild_Main_Roof", 5.2, 4.4, 2.6, (1.8, 2.2, 6.5), src, c_roof)
    create_box("Guild_Chimney", (0.8, 0.8, 2.5), (3.6, 2.4, 8.0), src, c_stone)

    # --- Right: Retaining Terrace & Elevated Watch-Stair (X: 4.2 to 8.5) ---
    create_box("Terrace_Retaining_Wall", (4.2, 4.2, 2.4), (6.3, 2.8, 1.2), src, c_plinth)
    create_box("Terrace_Stairs", (1.4, 2.2, 1.2), (4.5, 1.5, 0.6), src, c_plinth)
    create_box("Terrace_Upper_House", (3.8, 3.6, 3.4), (6.5, 3.2, 4.1), src, c_plaster)
    create_gable_roof("Terrace_House_Roof", 4.2, 4.0, 2.2, (6.5, 3.2, 5.8), src, c_roof)
    create_box("Terrace_Balcony_Rail", (3.8, 0.25, 0.9), (6.3, 0.8, 2.85), src, c_wood)

    # 4. Deep Background Silhouette (Y = 7.0 to 11.0)
    create_box("BG_Keep_CurtainWall", (16.0, 3.0, 7.0), (0.0, 8.0, 3.5), src, c_bg)
    create_box("BG_Keep_Tower", (3.0, 3.0, 10.0), (-3.5, 8.5, 5.0), src, c_bg)
    create_pyramid_spire("BG_Tower_Spire", 3.2, 3.2, 3.5, (-3.5, 8.5, 10.0), src, c_roof)
    create_gable_roof("BG_Distant_Rooftops", 7.0, 3.0, 2.5, (3.5, 8.5, 7.0), src, c_roof)

    # Lighting & World
    world = bpy.data.worlds.new("World_ClayA")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.58, 0.65, 0.76, 1.0)
        bg_node.inputs["Strength"].default_value = 0.8
    scene.world = world

    sun_data = bpy.data.lights.new("SunA", type='SUN')
    sun_data.energy = 2.8
    sun_data.color = (1.0, 0.96, 0.90)
    sun_obj = bpy.data.objects.new("SunA", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (0.75, 0.45, 0.35)

    # Walkers
    walker_path = str(REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png")
    p_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(-0.5, 0.0, 0.0), frame_width=24, frame_height=48, frame_index=0, world_height=1.75, name="TH_ACTOR_PROTAGONIST")
    colls["TH_PREVIEW_ACTORS"].objects.link(p_obj); scene.collection.objects.unlink(p_obj)

    npc1_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(2.8, 0.5, 0.0), frame_width=24, frame_height=48, frame_index=2, world_height=1.75, name="TH_ACTOR_NPC1")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc1_obj); scene.collection.objects.unlink(npc1_obj)

    npc2_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(5.8, 1.0, 2.4), frame_width=24, frame_height=48, frame_index=4, world_height=1.75, name="TH_ACTOR_NPC2")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc2_obj); scene.collection.objects.unlink(npc2_obj)

    # Render & Save
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    out_dir = REPO_ROOT / "tools" / "sterile_town" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "clay_A1.png"
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "lineage_A1_clay.blend"))
    print(f"A1 Clay Rendered & Saved.")

if __name__ == "__main__":
    build_lineage_a1()
