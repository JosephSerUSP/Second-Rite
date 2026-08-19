# gauntlet/pipeline/camera_rig.py
# DRPG presentation camera and 4-light studio presentation rig in Blender

import bpy
import math

def setup_drpg_camera(
    ortho_scale: float = 2.45,
    camera_z: float = 1.548,
    camera_y: float = -4.0,
    pitch_deg: float = 7.5
):
    """
    Sets up the global presentation camera for DRPG NPC sprites.
    Uses a slight front-oblique angle (7.5 degrees pitch down) with orthographic projection
    calibrated so that a 1.5m character renders at ~118-120px height on a 192x192 canvas,
    with feet planted solidly at the ground anchor (Y=176).
    """
    # Remove existing cameras
    for obj in list(bpy.data.objects):
        if obj.type == 'CAMERA':
            bpy.data.objects.remove(obj, do_unlink=True)

    cam_data = bpy.data.cameras.new(name="DRPG_Camera")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = ortho_scale
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100.0

    cam_obj = bpy.data.objects.new("DRPG_Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Position & Rotation
    pitch_rad = math.radians(90.0 - pitch_deg) # 82.5 degrees
    cam_obj.location = (0.0, camera_y, camera_z)
    cam_obj.rotation_euler = (pitch_rad, 0.0, 0.0)

    # Render settings: Crisp sprite definition
    scene = bpy.context.scene
    scene.render.resolution_x = 192
    scene.render.resolution_y = 192
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Sharp pixel filtering for pixel art / sprite clarity
    scene.render.filter_size = 0.5
    if hasattr(scene, "cycles"):
        scene.cycles.pixel_filter_type = 'BOX'

    # Color management: Standard sRGB High Contrast
    if hasattr(scene, "view_settings"):
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'High Contrast'

    return cam_obj

def setup_drpg_lighting():
    """
    Sets up neutral 4-point presentation lighting with subtle ambient bounce.
    Ensures forms, face planes, hands, and garment volumes read clearly without harsh black shadows
    or environment-specific color casts.
    """
    # Clear existing lights
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

    # 1. Key Light (Top-Right-Front, warm daylight, crisp definition)
    key_data = bpy.data.lights.new(name="Key_Light", type='SUN')
    key_data.energy = 1.8
    key_data.color = (1.0, 0.97, 0.92)
    key_obj = bpy.data.objects.new("Key_Light", key_data)
    key_obj.rotation_euler = (math.radians(45), math.radians(15), math.radians(-30))
    bpy.context.scene.collection.objects.link(key_obj)

    # 2. Fill Light (Left-Front, neutral soft fill)
    fill_data = bpy.data.lights.new(name="Fill_Light", type='SUN')
    fill_data.energy = 0.9
    fill_data.color = (0.90, 0.92, 0.95)
    fill_obj = bpy.data.objects.new("Fill_Light", fill_data)
    fill_obj.rotation_euler = (math.radians(35), math.radians(-25), math.radians(40))
    bpy.context.scene.collection.objects.link(fill_obj)

    # 3. Rim / Edge Light (Behind-Top, crisp rim to pop silhouette)
    rim_data = bpy.data.lights.new(name="Rim_Light", type='SUN')
    rim_data.energy = 1.4
    rim_data.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new("Rim_Light", rim_data)
    rim_obj.rotation_euler = (math.radians(-50), math.radians(10), math.radians(155))
    bpy.context.scene.collection.objects.link(rim_obj)

    # 4. Ground Bounce Light (Soft upward fill)
    bounce_data = bpy.data.lights.new(name="Bounce_Light", type='SUN')
    bounce_data.energy = 0.5
    bounce_data.color = (0.85, 0.82, 0.80)
    bounce_obj = bpy.data.objects.new("Bounce_Light", bounce_data)
    bounce_obj.rotation_euler = (math.radians(-80), 0.0, 0.0)
    bpy.context.scene.collection.objects.link(bounce_obj)

    # World background transparent
    if bpy.context.scene.world:
        bpy.context.scene.world.use_nodes = True
        bg_node = bpy.context.scene.world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs['Color'].default_value = (0.1, 0.1, 0.12, 1.0)
            bg_node.inputs['Strength'].default_value = 0.5
