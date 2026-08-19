# gauntlet/pipeline/test_calibration.py
import sys
import os

# Add worktree to sys.path if needed
worktree = r"C:\Users\josep\.gemini\antigravity\worktrees\Hichaukitoden\drpg_npc_adversarial_pipeline"
if worktree not in sys.path:
    sys.path.insert(0, worktree)

import bpy
import math
from gauntlet.pipeline.camera_rig import setup_drpg_camera, setup_drpg_lighting

# Clear mesh objects
bpy.ops.wm.read_factory_settings(use_empty=True)

setup_drpg_camera()
setup_drpg_lighting()

# Create a test calibration character: 1.6m tall standing on Z=0
# Feet at Z=0, head at Z=1.6
# Body cylinder
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.1, location=(0, 0, 0.75))
body = bpy.context.active_object
body.name = "Test_Body"

# Head sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(0, 0, 1.42))
head = bpy.context.active_object
head.name = "Test_Head"

# Feet bases
bpy.ops.mesh.primitive_cube_add(size=0.15, location=(-0.12, 0, 0.075))
bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0.12, 0, 0.075))

# Simple material
mat = bpy.data.materials.new(name="TestMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.3, 0.5, 0.8, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.4

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.data.materials.append(mat)

# Render to test file
out_path = os.path.join(worktree, "gauntlet", "calibration_test.png")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.context.scene.render.filepath = out_path

# Use EEVEE or Workbench or Cycles (let's check EEVEE / Cycles)
# In Blender 4.1, engine can be 'BLENDER_EEVEE' or 'CYCLES' or 'BLENDER_WORKBENCH'
bpy.context.scene.render.engine = 'BLENDER_EEVEE'

bpy.ops.render.render(write_still=True)
print(f"CALIBRATION RENDER DONE: {out_path}")
