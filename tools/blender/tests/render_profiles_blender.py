"""Real Blender smoke: profiles preserve calibrated projection and produce native pixels."""
import sys
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_profiles
import thestra_camera
import json
import tempfile

root = Path(__file__).resolve().parents[3]
record = json.loads((root / "tools/blender/fixtures/town_sideview_camera.json").read_text())
camera = thestra_camera.create_or_update_camera(record, make_active=True)
scene = bpy.context.scene
matrix = camera.matrix_world.copy()
lens, shift = camera.data.lens, camera.data.shift_y
for name in render_profiles.PROFILES:
    render_profiles.apply(scene, render_profiles.resolve(name))
    assert camera.matrix_world == matrix
    assert camera.data.lens == lens and camera.data.shift_y == shift
    assert scene.render.resolution_x == record["targetWidth"]
    assert scene.render.resolution_y == record["targetHeight"]
render_profiles.apply(scene, render_profiles.resolve("draft"))
scene.render.resolution_percentage = 100
with tempfile.TemporaryDirectory() as directory:
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(Path(directory) / "native.png")
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath)
    assert tuple(image.size) == (record["targetWidth"], record["targetHeight"]), tuple(image.size)
    bpy.data.images.remove(image)
print("RENDER_PROFILE_SMOKE_OK")
