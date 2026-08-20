'''Lineage A2 Refinement V3:
Fixes:
- Shifts camera forward to Y = -14.0 (Distance = 14.0 world units).
- Actor height projected: 1.75 * 512 / 14.0 = 64 px at Y=0 (or with distance = 18.67, keep Z=18.67 and scale architectural masses properly).
Let's analyze: at Z distance = 18.67, Walker screen height is 48.0 px.
The buildings in V2 have X span from -7.0 to +8.5 (total width 15.5 units).
At distance 18.67, horizontal screen span visible is 18.67 * (426 / (2 * 512 / 0.25)) = 18.67 * (426 / 2048) = 18.67 * 0.208 = 3.88 units on each side (total width ~7.8 units)!
THAT IS WHY only the middle 7.8 units were visible and the left arch was clipped off screen at X=-6.5!
Visible horizontal window at Y=0 is X = -3.9 to +3.9!
So architecture must be composed within X = -4.0 to +4.0 to be visible in the 426x240 frame!
'''
import sys
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

def build_lineage_a2():
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
    c_dark = make_clay("ClayDarkA", (0.08, 0.08, 0.10, 1.0))
    c_street = make_clay("ClayStreetA", (0.52, 0.50, 0.46, 1.0))
    c_bg = make_clay("ClayBgA", (0.64, 0.66, 0.72, 1.0))
    c_window = make_clay("ClayWindowA", (0.18, 0.22, 0.26, 1.0), roughness=0.3)

    src = colls["TH_SOURCE"]

    # Visible frame width at Y=0 is X: -3.8 to +3.8.
    # 1. Street Walkway with gutter
    create_box("Street_Cobbles", (16.0, 5.0, 0.8), (0.0, -0.5, -0.4), src, c_street)
    create_box("Street_Curb_Stone", (16.0, 0.35, 0.15), (0.0, 0.8, 0.075), src, c_plinth)

    # 2. Foreground Ruined Archway & Mounting Step (Left, Y = -2.4, X = -3.2)
    create_box("FG_Arch_Pier_Base", (0.8, 0.8, 1.4), (-3.3, -2.4, 0.7), src, c_plinth)
    create_box("FG_Arch_Pier_Shaft", (0.6, 0.6, 4.2), (-3.3, -2.4, 3.5), src, c_stone)
    create_box("FG_Arch_Voussoir", (1.4, 0.6, 0.8), (-2.6, -2.4, 5.6), src, c_stone)
    create_box("FG_Mounting_Stone", (0.8, 0.6, 0.5), (-2.5, -2.4, 0.25), src, c_plinth)

    # 3. Action Midground (Y = 1.5 to 4.5)
    # --- Left: Fortified Bastion Gate Arch (X: -3.6 to -1.2) ---
    create_box("Bastion_Flank_Wall", (1.2, 3.8, 5.5), (-3.0, 2.8, 2.75), src, c_stone)
    create_box("Bastion_Flank_Plinth", (1.4, 4.0, 0.8), (-3.0, 2.8, 0.4), src, c_plinth)
    create_box("Bastion_Machicolation", (1.5, 4.2, 0.5), (-3.0, 2.8, 5.75), src, c_stone)
    create_pyramid_spire("Bastion_Tower_Roof", 1.5, 4.2, 2.0, (-3.0, 2.8, 6.0), src, c_roof)
    
    # Grand Arched Gateway Portal (X: -2.2 to -0.6, Z: 0.0 to 3.2)
    create_box("Gate_Arch_LeftJamb", (0.4, 2.8, 3.0), (-2.2, 2.6, 1.5), src, c_plinth)
    create_box("Gate_Arch_RightJamb", (0.4, 2.8, 3.0), (-0.6, 2.6, 1.5), src, c_plinth)
    create_box("Gate_Arch_Span", (2.0, 2.8, 0.8), (-1.4, 2.6, 3.4), src, c_stone)
    create_box("Gate_Arch_Impost_L", (0.5, 3.0, 0.15), (-2.2, 2.6, 3.0), src, c_stone)
    create_box("Gate_Arch_Impost_R", (0.5, 3.0, 0.15), (-0.6, 2.6, 3.0), src, c_stone)
    # Deep inner barrel vaulted tunnel revealing depth
    create_box("Gate_Deep_Vault_Interior", (1.6, 5.0, 3.0), (-1.4, 5.0, 1.5), src, c_dark)

    # --- Center: Merchant Guildhouse with Enterable Ground Doorway (X: -0.4 to 2.8) ---
    # Ground floor stone masonry (Z = 0.0 to 2.8)
    create_box("Guild_Ground_Plinth", (3.2, 3.6, 0.4), (1.2, 2.6, 0.2), src, c_plinth)
    create_box("Guild_Stone_Wall_L", (0.8, 3.4, 2.4), (0.0, 2.6, 1.6), src, c_stone)
    create_box("Guild_Stone_Wall_R", (1.0, 3.4, 2.4), (2.3, 2.6, 1.6), src, c_stone)
    create_box("Guild_Stone_Lintel", (3.2, 3.4, 0.4), (1.2, 2.6, 3.0), src, c_stone)

    # Enterable portal at Z=0 (doorway cavity, frame and low step)
    create_box("Guild_Door_Cavity", (1.2, 2.5, 2.4), (1.0, 3.8, 1.2), src, c_dark)
    create_box("Guild_Door_Frame", (1.1, 0.2, 2.3), (1.0, 1.8, 1.15), src, c_wood)
    create_box("Guild_Stone_Sill", (1.3, 0.5, 0.15), (1.0, 1.2, 0.075), src, c_plinth)
    
    # Ground floor shuttered shop window (Right side)
    create_box("Guild_Shop_Window_Frame", (0.8, 0.2, 1.2), (2.3, 0.9, 1.6), src, c_wood)
    create_box("Guild_Shop_Window_Glass", (0.7, 0.1, 1.0), (2.3, 0.95, 1.6), src, c_window)
    create_box("Guild_Shop_Sill", (0.9, 0.3, 0.12), (2.3, 0.8, 0.95), src, c_plinth)

    # Timber Jetty Second Story (Z = 3.2 to 5.8)
    create_box("Guild_Jetty_Box", (3.4, 4.0, 2.6), (1.2, 2.2, 4.5), src, c_plaster)
    create_box("Guild_Corbel_Beam_1", (0.25, 0.8, 0.3), (-0.2, 0.6, 3.1), src, c_wood)
    create_box("Guild_Corbel_Beam_2", (0.25, 0.8, 0.3), (0.6, 0.6, 3.1), src, c_wood)
    create_box("Guild_Corbel_Beam_3", (0.25, 0.8, 0.3), (1.6, 0.6, 3.1), src, c_wood)
    create_box("Guild_Corbel_Beam_4", (0.25, 0.8, 0.3), (2.6, 0.6, 3.1), src, c_wood)
    
    # Timber framing ribs
    create_box("Guild_Timber_BottomRail", (3.5, 0.15, 0.2), (1.2, 0.1, 3.3), src, c_wood)
    create_box("Guild_Timber_TopRail", (3.5, 0.15, 0.2), (1.2, 0.1, 5.7), src, c_wood)
    create_box("Guild_Timber_Stud_L", (0.15, 0.15, 2.4), (-0.4, 0.1, 4.5), src, c_wood)
    create_box("Guild_Timber_Stud_M1", (0.15, 0.15, 2.4), (0.4, 0.1, 4.5), src, c_wood)
    create_box("Guild_Timber_Stud_M2", (0.15, 0.15, 2.4), (1.6, 0.1, 4.5), src, c_wood)
    create_box("Guild_Timber_Stud_R", (0.15, 0.15, 2.4), (2.8, 0.1, 4.5), src, c_wood)
    
    # Second floor oriel window
    create_box("Guild_Oriel_Window", (1.2, 0.4, 1.4), (1.0, 0.0, 4.6), src, c_wood)
    create_box("Guild_Oriel_Glass", (1.0, 0.1, 1.2), (1.0, -0.15, 4.6), src, c_window)

    # Roof structure
    create_gable_roof("Guild_Main_Roof", 3.8, 4.4, 2.2, (1.2, 2.2, 5.8), src, c_roof)
    create_box("Guild_Chimney", (0.6, 0.6, 2.0), (2.5, 2.4, 6.8), src, c_stone)
    create_box("Guild_Chimney_Pot", (0.3, 0.3, 0.5), (2.5, 2.4, 7.9), src, c_roof)

    # --- Right: Retaining Terrace & Elevated Watch-Stair (X: 3.0 to 5.5) ---
    create_box("Terrace_Retaining_Wall", (2.6, 4.2, 2.4), (4.2, 2.8, 1.2), src, c_plinth)
    create_box("Terrace_Stair_1", (0.8, 0.5, 0.3), (3.0, 1.2, 0.15), src, c_plinth)
    create_box("Terrace_Stair_2", (0.8, 0.5, 0.6), (3.0, 1.7, 0.45), src, c_plinth)
    create_box("Terrace_Stair_3", (0.8, 0.5, 0.9), (3.0, 2.2, 0.75), src, c_plinth)
    create_box("Terrace_Upper_House", (2.4, 3.6, 3.2), (4.4, 3.2, 4.0), src, c_plaster)
    create_box("Terrace_Upper_Window", (0.8, 0.2, 1.0), (4.4, 1.3, 4.2), src, c_window)
    create_gable_roof("Terrace_House_Roof", 2.8, 4.0, 1.8, (4.4, 3.2, 5.6), src, c_roof)
    create_box("Terrace_Balcony_Rail", (2.4, 0.2, 0.8), (4.2, 0.8, 2.8), src, c_wood)

    # 4. Deep Background Silhouette (Y = 7.0 to 11.0)
    create_box("BG_Keep_CurtainWall", (16.0, 3.0, 7.0), (0.0, 8.0, 3.5), src, c_bg)
    create_box("BG_Keep_Tower", (2.4, 2.4, 10.0), (-2.5, 8.5, 5.0), src, c_bg)
    create_pyramid_spire("BG_Tower_Spire", 2.6, 2.6, 3.2, (-2.5, 8.5, 10.0), src, c_roof)
    create_gable_roof("BG_Distant_Rooftops", 6.0, 3.0, 2.2, (2.5, 8.5, 6.8), src, c_roof)

    # Lighting & World
    world = bpy.data.worlds.new("World_ClayA2")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.58, 0.65, 0.76, 1.0)
        bg_node.inputs["Strength"].default_value = 0.8
    scene.world = world

    sun_data = bpy.data.lights.new("SunA2", type='SUN')
    sun_data.energy = 2.8
    sun_data.color = (1.0, 0.96, 0.90)
    sun_obj = bpy.data.objects.new("SunA2", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (0.75, 0.45, 0.35)

    # Walkers
    walker_path = str(REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png")
    p_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(-0.4, 0.0, 0.0), frame_width=24, frame_height=48, frame_index=0, world_height=1.75, name="TH_ACTOR_PROTAGONIST")
    colls["TH_PREVIEW_ACTORS"].objects.link(p_obj); scene.collection.objects.unlink(p_obj)

    npc1_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(1.8, 0.4, 0.0), frame_width=24, frame_height=48, frame_index=2, world_height=1.75, name="TH_ACTOR_NPC1")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc1_obj); scene.collection.objects.unlink(npc1_obj)

    npc2_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(3.8, 1.0, 2.4), frame_width=24, frame_height=48, frame_index=4, world_height=1.75, name="TH_ACTOR_NPC2")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc2_obj); scene.collection.objects.unlink(npc2_obj)

    # Render & Save
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    out_dir = REPO_ROOT / "tools" / "sterile_town" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "refined_A2.png"
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "lineage_A2_refined.blend"))
    print(f"A2 Refined V3 Rendered & Saved.")

if __name__ == "__main__":
    build_lineage_a2()
