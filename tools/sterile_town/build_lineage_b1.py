'''Lineage B1: The Sunken Canal / Lockside Alley
Polygonal geometry with sloped roofs, quayside canal basin, wooden cranes, timber jetties, and deep cargo vaults.
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

def build_lineage_b1():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    colls = {name: bpy.data.collections.new(name) for name in ["TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_CAMERA_PREVIEW"]}
    for c in colls.values(): scene.collection.children.link(c)
    cam_obj = setup_camera(scene, colls["TH_CAMERA_PREVIEW"])

    c_quay = make_clay("ClayQuayB", (0.52, 0.54, 0.56, 1.0))
    c_water = make_clay("ClayWaterB", (0.22, 0.32, 0.40, 1.0), roughness=0.15)
    c_timber = make_clay("ClayTimberB", (0.38, 0.28, 0.22, 1.0))
    c_plaster = make_clay("ClayPlasterB", (0.82, 0.80, 0.74, 1.0))
    c_roof = make_clay("ClayRoofB", (0.52, 0.32, 0.26, 1.0))
    c_dark = make_clay("ClayDarkB", (0.10, 0.10, 0.12, 1.0))
    c_bg = make_clay("ClayBgB", (0.62, 0.64, 0.68, 1.0))

    src = colls["TH_SOURCE"]

    # 1. Foreground Canal Basin (Y = -3.5 to -1.0, Z = -1.2)
    create_box("Water_Surface", (26.0, 4.5, 0.4), (0.0, -2.5, -1.2), src, c_water)
    create_box("FG_MooringPost_1", (0.35, 0.35, 2.2), (-5.5, -1.5, -0.1), src, c_timber)
    create_box("FG_MooringPost_2", (0.35, 0.35, 2.0), (-3.5, -1.5, -0.2), src, c_timber)
    
    # Right Foreground Harbor Crane / Cargo Derrick
    create_box("FG_Crane_Base", (0.8, 0.8, 0.6), (5.8, -2.0, -0.9), src, c_quay)
    create_box("FG_Crane_Mast", (0.45, 0.45, 5.2), (5.8, -2.0, 1.7), src, c_timber)
    create_box("FG_Crane_Boom", (3.2, 0.35, 0.35), (4.5, -2.0, 3.8), src, c_timber)
    create_box("FG_Cargo_Bales", (1.4, 1.2, 0.9), (4.8, -1.4, -0.75), src, c_timber)

    # 2. Main Quayside Walkway (Action plane at Y = 0.0, Z = 0.0)
    create_box("Quayside_Embankment", (26.0, 3.5, 1.6), (0.0, 0.2, -0.8), src, c_quay)
    create_box("Quayside_TimberCurb", (26.0, 0.3, 0.25), (0.0, -1.2, 0.125), src, c_timber)

    # 3. Midground Architecture (Y = 1.8 to 4.5)
    # --- Left: High Warehouse with Deep Barrel Vault (X: -6.5 to -2.0) ---
    create_box("Warehouse_Stone_Base", (4.8, 3.8, 2.5), (-4.5, 2.8, 1.25), src, c_quay)
    create_box("Warehouse_Upper_Plaster", (4.6, 3.6, 3.2), (-4.5, 2.8, 4.1), src, c_plaster)
    create_box("Warehouse_Timber_Frame", (4.8, 0.3, 3.2), (-4.5, 0.9, 4.1), src, c_timber)
    create_gable_roof("Warehouse_Roof", 5.0, 4.0, 2.4, (-4.5, 2.8, 5.7), src, c_roof)
    # Recessed ground-level cargo portal
    create_box("Warehouse_Vault_Cavity", (2.4, 3.0, 2.6), (-3.5, 3.2, 1.3), src, c_dark)
    create_box("Warehouse_Vault_Arch", (2.6, 0.4, 0.6), (-3.5, 1.0, 2.6), src, c_quay)

    # --- Center: Quayside Inn / Tavern with Porch & Enterable Doorway (X: -1.0 to 3.6) ---
    create_box("Tavern_Stone_Ground", (4.4, 3.6, 2.6), (1.3, 2.8, 1.3), src, c_quay)
    # Enterable Inn Doorway (X = 0.8, Y = 2.0, Z = 0.0)
    create_box("Tavern_Door_Cavity", (1.5, 2.4, 2.5), (0.8, 3.4, 1.25), src, c_dark)
    create_box("Tavern_Door_TimberFrame", (1.4, 0.2, 2.4), (0.8, 2.1, 1.2), src, c_timber)
    create_box("Tavern_Porch_Canopy", (2.6, 1.5, 0.25), (0.8, 1.3, 2.7), src, c_timber)
    create_box("Tavern_Porch_Post", (0.2, 0.2, 2.7), (1.9, 0.6, 1.35), src, c_timber)
    # Overhanging Jetty Second Floor with timber frame
    create_box("Tavern_Jetty_Floor", (4.8, 4.0, 2.8), (1.3, 2.4, 4.0), src, c_plaster)
    create_box("Tavern_Timber_Ribs", (4.9, 0.2, 2.8), (1.3, 0.3, 4.0), src, c_timber)
    create_gable_roof("Tavern_Gable_Roof", 5.2, 4.4, 2.5, (1.3, 2.4, 5.4), src, c_roof)
    create_box("Tavern_Chimney", (0.7, 0.7, 2.2), (3.0, 2.6, 7.0), src, c_quay)

    # --- Right: Sluice Bridge & Harbor Watchtower (X: 3.8 to 8.5) ---
    create_box("Sluice_Abutment", (4.2, 4.2, 2.2), (6.2, 2.8, 1.1), src, c_quay)
    create_box("Sluice_Arch_Cavity", (2.2, 3.5, 2.2), (5.5, 2.8, 1.1), src, c_dark)
    create_box("Sluice_Gatehouse_Tower", (3.6, 3.6, 5.2), (6.5, 3.2, 4.8), src, c_plaster)
    create_gable_roof("Sluice_Tower_Roof", 4.0, 4.0, 2.2, (6.5, 3.2, 7.4), src, c_roof)

    # 4. Deep Background Architecture (Y = 7.0 to 11.0)
    create_box("BG_Canal_Warehouses", (16.0, 3.5, 7.0), (0.0, 8.5, 3.5), src, c_bg)
    create_box("BG_Distant_Tower", (2.4, 2.4, 10.0), (-2.5, 9.0, 5.0), src, c_bg)
    create_pyramid_spire("BG_Tower_Spire", 2.6, 2.6, 3.0, (-2.5, 9.0, 10.0), src, c_roof)

    # Lighting & World
    world = bpy.data.worlds.new("World_ClayB")
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.55, 0.62, 0.74, 1.0)
        bg_node.inputs["Strength"].default_value = 0.8
    scene.world = world

    sun_data = bpy.data.lights.new("SunB", type='SUN')
    sun_data.energy = 2.8
    sun_data.color = (1.0, 0.95, 0.88)
    sun_obj = bpy.data.objects.new("SunB", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (0.80, 0.35, 0.50)

    # Walkers
    walker_path = str(REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png")
    p_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(-1.0, 0.0, 0.0), frame_width=24, frame_height=48, frame_index=0, world_height=1.75, name="TH_ACTOR_PROTAGONIST")
    colls["TH_PREVIEW_ACTORS"].objects.link(p_obj); scene.collection.objects.unlink(p_obj)

    npc1_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(1.2, 0.5, 0.0), frame_width=24, frame_height=48, frame_index=3, world_height=1.75, name="TH_ACTOR_NPC1")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc1_obj); scene.collection.objects.unlink(npc1_obj)

    npc2_obj = thestra_camera.create_actor_preview(walker_path, cam_obj, anchor=(5.6, 1.2, 2.2), frame_width=24, frame_height=48, frame_index=5, world_height=1.75, name="TH_ACTOR_NPC2")
    colls["TH_PREVIEW_ACTORS"].objects.link(npc2_obj); scene.collection.objects.unlink(npc2_obj)

    # Render & Save
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    out_dir = REPO_ROOT / "tools" / "sterile_town" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "clay_B1.png"
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "lineage_B1_clay.blend"))
    print(f"B1 Clay Rendered & Saved.")

if __name__ == "__main__":
    build_lineage_b1()
