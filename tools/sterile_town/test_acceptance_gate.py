'''First Acceptance Gate test script.
Proves camera calibration, level baseline, lens family, and Walker billboard presentation.
'''
import os
import sys
import json
import bpy
from pathlib import Path

# Add tools/blender to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))
import thestra_camera

def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    target_w, target_h = 426, 240
    base_w, base_h = 256, 144
    fov_half_x = 0.25
    fov_half_y = fov_half_x * (base_h / base_w) # 0.140625

    calib_record = {
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
        "eye": {"x": 0.0, "y": -18.66666667, "z": 0.0},
        "orientation": {
            "forwardX": 0.0,
            "forwardY": 1.0,
            "rightX": 1.0,
            "rightY": 0.0,
            "pitchRadians": 0.0
        },
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        }
    }

    cam_obj = thestra_camera.create_or_update_camera(calib_record, scene=scene, make_active=True)

    # Add ground plane reference
    mesh = bpy.data.meshes.new("GroundMesh")
    ground_obj = bpy.data.objects.new("GroundPlane", mesh)
    scene.collection.objects.link(ground_obj)
    mesh.from_pydata([
        (-15.0, -10.0, 0.0),
        ( 15.0, -10.0, 0.0),
        ( 15.0,  10.0, 0.0),
        (-15.0,  10.0, 0.0),
    ], [], [(0, 1, 2, 3)])
    mesh.update()

    # Simple material for ground
    mat = bpy.data.materials.new("GroundMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.25, 0.25, 0.25, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    mesh.materials.append(mat)

    # Lighting
    light_data = bpy.data.lights.new(name="SunLight", type='SUN')
    light_data.energy = 2.0
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    scene.collection.objects.link(light_obj)
    light_obj.rotation_euler = (0.785, 0.5, 0.5)

    # Ambient world
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.5, 0.6, 0.7, 1.0)
        bg.inputs["Strength"].default_value = 0.6
    scene.world = world

    # Walker sprite
    walker_path = str(REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png")

    # Protagonist (center, frame 0)
    thestra_camera.create_actor_preview(
        walker_path, cam_obj,
        anchor=(0.0, 0.0, 0.0),
        frame_width=24, frame_height=48, frame_index=0,
        world_height=1.75, name="TH_ACTOR_PROTAGONIST"
    )

    # NPC 1 (left, frame 2)
    thestra_camera.create_actor_preview(
        walker_path, cam_obj,
        anchor=(-3.0, 0.0, 0.0),
        frame_width=24, frame_height=48, frame_index=2,
        world_height=1.75, name="TH_ACTOR_NPC1"
    )

    # NPC 2 (right, frame 4)
    thestra_camera.create_actor_preview(
        walker_path, cam_obj,
        anchor=(3.0, 0.0, 0.0),
        frame_width=24, frame_height=48, frame_index=4,
        world_height=1.75, name="TH_ACTOR_NPC2"
    )

    # Render settings
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    out_dir = REPO_ROOT / "tools" / "sterile_town" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "acceptance_gate_1.png"
    scene.render.filepath = str(out_path)

    bpy.ops.render.render(write_still=True)
    print(f"Rendered Acceptance Gate 1 to {out_path}")

    # Project world points and check pixel dimensions
    p_feet = thestra_camera.project_world_point(scene, cam_obj, (0.0, 0.0, 0.0))
    p_head = thestra_camera.project_world_point(scene, cam_obj, (0.0, 0.0, 1.75))
    h_px = abs(p_feet[1] - p_head[1])
    print(f"Projected Protagonist Screen Height: {h_px:.2f} px (target: ~48 px)")
    print(f"Feet projection: X={p_feet[0]:.2f}, Y={p_feet[1]:.2f} (expected Y around horizon Y=110)")

    if abs(h_px - 48.0) > 1.0:
        raise ValueError(f"Actor height projection failed: {h_px:.2f} != 48 px")

if __name__ == "__main__":
    run()
