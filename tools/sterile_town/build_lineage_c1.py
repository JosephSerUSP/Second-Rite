'''Lineage C1: The Monastic Cloister & Scriptorium Arcade
True arcade bays, carved capitals, vaulted chapterhouse portal, clerestory wall, high slate roofs and bell tower.
Camera Eye Z = 2.37.
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

def build_lineage_c1():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    colls = {name: bpy.data.collections.new(name) for name in ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]}
    for c in colls.values(): scene.collection.children.link(c)
    cam_obj = setup_camera(scene, colls["TH_CAMERA_PREVIEW"])

    c_ashlar = make_clay("ClayAshlarC", (0.80, 0.78, 0.74, 1.0))
    c_carved = make_clay("ClayCarvedC", (0.65, 0.62, 0.58, 1.0))
    c_slate = make_clay("ClaySlateC", (0.36, 0.38, 0.44, 1.0))
    c_dark = make_clay("ClayDarkC", (0.10, 0.10, 0.12, 1.0))
    c_floor = make_clay("ClayPavingC", (0.58, 0.56, 0.52, 1.0))
    c_bg = make_clay("ClayBgC", (0.68, 0.70, 0.74, 1.0))

    src = colls["TH_SOURCE"]

    # 1. Floor Gallery / Flagstone Walkway (Action plane at Y = 0.0, Z = 0.0)
    create_box("Cloister_Flagstones", (26.0, 5.0, 0.8), (0.0, -0.5, -0.4), src, c_floor)

    # 2. Foreground Arcaded Parapet & Shrubbery Planter (Left at Y = -2.2)
    create_box("FG_Parapet_Base", (4.5, 0.6, 1.2), (-5.2, -2.2, 0.6), src, c_ashlar)
    create_box("FG_Parapet_Coping", (4.8, 0.8, 0.2), (-5.2, -2.2, 1.3), src, c_carved)
    create_box("FG_Parapet_Pillar", (0.8, 0.8, 2.2), (-3.0, -2.2, 1.1), src, c_ashlar)

    # 3. Main Action Midground - Scriptorium Arcade (Y = 1.2 to 4.5)
    # Rhythmic arcade piers along gallery walk
    create_box("Arcade_Pier_1", (0.9, 1.2, 3.8), (-4.5, 1.8, 1.9), src, c_ashlar)
    create_box("Arcade_Capital_1", (1.1, 1.4, 0.3), (-4.5, 1.8, 3.95), src, c_carved)
    
    create_box("Arcade_Pier_2", (0.9, 1.2, 3.8), (-1.8, 1.8, 1.9), src, c_ashlar)
    create_box("Arcade_Capital_2", (1.1, 1.4, 0.3), (-1.8, 1.8, 3.95), src, c_carved)
    
    # Left Arch Span
    create_box("Arcade_Arch_Left", (2.0, 1.2, 1.0), (-3.15, 1.8, 4.4), src, c_carved)
    # Recessed Vault Alcove behind left arch
    create_box("Arcade_Vault_Alcove_L", (2.2, 2.8, 3.6), (-3.15, 3.5, 1.8), src, c_dark)

    # Center Portal Bay / Heavy Chapterhouse Doorway (X = -0.5 to 2.5)
    create_box("Arcade_Pier_3", (0.9, 1.2, 3.8), (1.5, 1.8, 1.9), src, c_ashlar)
    create_box("Arcade_Capital_3", (1.1, 1.4, 0.3), (1.5, 1.8, 3.95), src, c_carved)
    create_box("Arcade_Arch_Center", (2.6, 1.2, 1.0), (-0.15, 1.8, 4.4), src, c_carved)
    
    # Enterable portal with deep stone jambs & tympanum
    create_box("Chapterhouse_Portal_Frame", (1.8, 0.6, 3.0), (-0.15, 2.4, 1.5), src, c_carved)
    create_box("Chapterhouse_Door_Cavity", (1.4, 2.5, 2.6), (-0.15, 3.5, 1.3), src, c_dark)
    create_box("Chapterhouse_Tympanum", (1.6, 0.4, 0.8), (-0.15, 2.2, 3.0), src, c_carved)

    # Right Pier 4 & Right Arch Span
    create_box("Arcade_Pier_4", (0.9, 1.2, 3.8), (4.2, 1.8, 1.9), src, c_ashlar)
    create_box("Arcade_Capital_4", (1.1, 1.4, 0.3), (4.2, 1.8, 3.95), src, c_carved)
    create_box("Arcade_Arch_Right", (2.0, 1.2, 1.0), (2.85, 1.8, 4.4), src, c_carved)
    create_box("Arcade_Vault_Alcove_R", (2.0, 2.8, 3.6), (2.85, 3.5, 1.8), src, c_dark)

    # Upper Clerestory Wall with Cornice & Slate Gable Roof (Z = 4.8 to 9.5)
    create_box("Upper_Clerestory_Wall", (11.0, 3.5, 2.8), (0.0, 2.8, 6.3), src, c_ashlar)
    create_box("Upper_Cornice_Molding", (11.4, 3.8, 0.35), (0.0, 2.8, 7.85), src, c_carved)
    create_gable_roof("Cathedral_High_Roof", 11.2, 4.0, 2.4, (0.0, 2.8, 8.0), src, c_slate)

    # Right Grand Bell Tower Buttress (X = 4.8 to 8.5, Y = 2.4)
    create_box("BellTower_Base", (3.6, 4.2, 8.5), (6.2, 2.8, 4.25), src, c_ashlar)
    create_box("BellTower_Belfry_Opening", (1.8, 3.0, 2.6), (6.2, 2.8, 6.8), src, c_dark)
    create_box("BellTower_Cornice", (4.0, 4.6, 0.4), (6.2, 2.8, 8.7), src, c_carved)
    create_pyramid_spire("BellTower_Pyramidal_Spire", 4.0, 4.6, 3.2, (6.2, 2.8, 8.9), src, c_slate)

    # 4. Deep Distant Cloister Architecture (Y = 6.5 to 11.0)
    create_box("BG_Abbey_Apse", (6.0, 4.0, 8.0), (-4.0, 8.0, 4.0), src, c_bg)
    create_box("BG_Flying_Buttress", (1.2, 3.5, 4.5), (-1.5, 7.0, 5.0), src, c_bg)
    create_pyramid_spire("BG_Distant_Cathedral_Spire", 2.6, 2.6, 6.0, (-3.5, 9.0, 7.0), src, c_slate)

    # Lighting & World
    world = bpy.data.worlds.new("World_ClayC")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.62, 0.68, 0.78, 1.0)
        bg_node.inputs["Strength"].default_value = 0.8
    scene.world = world

    sun_data = bpy.data.lights.new("SunC", type='SUN')
    sun_data.energy = 2.8
    sun_data.color = (1.0, 0.98, 0.92)
    sun_obj = bpy.data.objects.new("SunC", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (0.70, 0.40, 0.40)

    # Walkers
    walker_path = str(REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png")
    p_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(-2.0, 0.0, 0.0), frame_width=24, frame_height=48, frame_index=0, world_height=1.75, name="TH_ACTOR_PROTAGONIST")
    colls["TH_PREVIEW_ACTORS"].objects.link(p_obj); scene.collection.objects.unlink(p_obj)

    npc1_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(-0.15, 0.6, 0.0), frame_width=24, frame_height=48, frame_index=1, world_height=1.75, name="TH_ACTOR_NPC1")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc1_obj); scene.collection.objects.unlink(npc1_obj)

    npc2_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(3.2, 0.4, 0.0), frame_width=24, frame_height=48, frame_index=4, world_height=1.75, name="TH_ACTOR_NPC2")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc2_obj); scene.collection.objects.unlink(npc2_obj)

    # Render & Save
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    out_dir = REPO_ROOT / "tools" / "sterile_town" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "clay_C1.png"
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "lineage_C1_clay.blend"))
    print(f"C1 Clay Rendered & Saved.")

if __name__ == "__main__":
    build_lineage_c1()
