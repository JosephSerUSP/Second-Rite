"""Real projection bake: front paint, unseen fallback, occlusion and translated root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from atlas_allocation import pack
from view_projection import project_view, projection_material, world_mesh

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(location=(3, 2, 1))
obj = bpy.context.object; obj.name = 'Receiver'
original = obj.data.uv_layers.new(name='OriginalUV')
for p in obj.data.polygons:
    for li, uv in zip(p.loop_indices, [(0,0),(1,0),(1,1),(0,1)]): original.data[li].uv = uv
original_values = [tuple(d.uv) for d in original.data]
obj.data.uv_layers.new(name='BakedUV'); obj.data.uv_layers.active = obj.data.uv_layers['BakedUV']
pack(obj, 128, 3)
obj.data.uv_layers['BakedUV'].active_render = True
before = [tuple(v.co) for v in obj.data.vertices]
scene = bpy.context.scene; scene.render.resolution_x = scene.render.resolution_y = 128
scene.render.resolution_percentage = 100
cam = bpy.data.objects.new('ReferenceCamera', bpy.data.cameras.new('ReferenceCamera'))
scene.collection.objects.link(cam); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 4
cam.location = (3, -8, 1); cam.rotation_euler = Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
args = dict(name='front', image_size=(8,8), rectangle=(1,1,7,7), clip=(0,0,8,8))
view = project_view(obj, scene, cam, **args)
assert obj.data.uv_layers.active.name == 'BakedUV'
assert [tuple(d.uv) for d in obj.data.uv_layers['OriginalUV'].data] == original_values
assert before == [tuple(v.co) for v in obj.data.vertices]
projected_u = sorted(set(round(d.uv.x, 6) for d in obj.data.uv_layers[view['uvLayer']].data))
assert projected_u == [.3125, .6875], projected_u  # Camera pixels, not silhouette autofit.
front = next(p for p in obj.data.polygons if p.normal.y < -.9)
back = next(p for p in obj.data.polygons if p.normal.y > .9)
attr = obj.data.attributes[view['visibilityAttribute']]
assert all(attr.data[li].value == 1 for li in front.loop_indices)
assert all(attr.data[li].value == 0 for li in back.loop_indices)
try: project_view(obj, scene, cam, **args)
except ValueError: pass
else: raise AssertionError('Existing projection overwritten')
try: project_view(obj, scene, cam, name='bad', image_size=(8,8), rectangle=(0,0,9,7), clip=(0,0,8,8))
except ValueError: pass
else: raise AssertionError('Out-of-image calibration accepted')
cam.data.type = 'PERSP'
try: project_view(obj, scene, cam, name='bad', image_size=(8,8), rectangle=(1,1,7,7), clip=(0,0,8,8))
except ValueError: pass
else: raise AssertionError('Unsupported perspective accepted')
cam.data.type = 'ORTHO'

image = bpy.data.images.new('RedReference', 8, 8, alpha=True)
image.pixels[:] = [1,0,0,1] * 64
fallback = bpy.data.images.new('BlueFallback', 8, 8, alpha=True)
fallback.pixels[:] = [0,0,1,1] * 64
mat, control = projection_material('ProjectionRecipe', image, [view], fallback)
obj.data.materials.clear(); obj.data.materials.append(mat)
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 1
scene.render.bake.use_selected_to_active = False; scene.render.bake.margin = 1
scene.render.bake.use_clear = True
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
atlas = bpy.data.images.new('ActualBake', 128, 128, alpha=False)
node = mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image = atlas; mat.node_tree.nodes.active = node
def sample(poly):
    uv = obj.data.uv_layers['BakedUV']
    centre = sum((uv.data[li].uv for li in poly.loop_indices), Vector((0,0))) / len(poly.loop_indices)
    pixel = (int(centre.y * 128) * 128 + int(centre.x * 128)) * 4
    return list(atlas.pixels[pixel:pixel+3])
bpy.ops.object.bake(type='EMIT')
assert sample(front)[0] > .99 and sample(front)[2] < .01, sample(front)
assert sample(back)[2] > .99 and sample(back)[0] < .01, sample(back)
control.inputs[0].default_value = 1; bpy.ops.object.bake(type='EMIT')
assert sample(front)[1] > .99 and sample(back)[0] > .99, (sample(front),sample(back))

# Two equally weighted correspondences blend actual colours in linear light.
image.pixels[:] = sum(([1,0,0,1] if x < 4 else [0,1,0,1]
                      for y in range(8) for x in range(8)), [])
image.update()
left = project_view(obj, scene, cam, name='red_half', image_size=(8,8), rectangle=(.5,1,3.5,7), clip=(0,0,4,8))
right = project_view(obj, scene, cam, name='green_half', image_size=(8,8), rectangle=(4.5,1,7.5,7), clip=(4,0,8,8))
blend, switch = projection_material('TwoViews', image, [left,right], fallback)
obj.data.materials.clear(); obj.data.materials.append(blend)
node = blend.node_tree.nodes.new('ShaderNodeTexImage'); node.image = atlas; blend.node_tree.nodes.active = node
bpy.ops.object.bake(type='EMIT')
assert min(sample(front)[:2]) > .65 and abs(sample(front)[0]-sample(front)[1]) < .02 and sample(front)[2] < .01, sample(front)
assert sample(back)[2] > .99, sample(back)

# Opaque paint may use an independent RGBA support mask from the actual render.
mask = bpy.data.images.new('EmptyRenderSupport', 8, 8, alpha=True)
mask.pixels[:] = [0,0,0,0] * 64
masked, switch = projection_material('MaskedPaint', image, [left], fallback, mask_image=mask)
obj.data.materials.clear(); obj.data.materials.append(masked)
node = masked.node_tree.nodes.new('ShaderNodeTexImage'); node.image = atlas; masked.node_tree.nodes.active = node
bpy.ops.object.bake(type='EMIT')
assert sample(front)[2] > .99 and sample(front)[0] < .01, sample(front)

# A larger component between the camera and receiver must reject front samples.
bpy.ops.mesh.primitive_cube_add(size=2.6, location=(3,-1,1)); blocker = bpy.context.object
bpy.context.view_layer.update(); points = world_mesh(obj) + world_mesh(blocker)
faces = [tuple(p.vertices) for p in obj.data.polygons] + [tuple(i+8 for i in p.vertices) for p in blocker.data.polygons]
tree = BVHTree.FromPolygons(points, faces)
hidden = project_view(obj, scene, cam, name='occluded', image_size=(8,8), rectangle=(1,1,7,7), clip=(0,0,8,8), tree=tree)
attr = obj.data.attributes[hidden['visibilityAttribute']]
assert all(attr.data[li].value == 0 for li in front.loop_indices)
print('VIEW PROJECTION FIXTURE OK: actual colour/coverage, multiview blend and support-mask bakes, unseen fallback, occlusion, UV preservation, calibration rejection')
