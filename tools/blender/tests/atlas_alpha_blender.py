import bpy,sys,numpy as np,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import atlas_alpha
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_plane_add(size=2)
o=bpy.context.object
m=bpy.data.materials.new('leaf');m.use_nodes=True
t=m.node_tree.nodes.new('ShaderNodeTexImage')
im=bpy.data.images.new('leaf_texture',8,8,alpha=True)
a=np.ones((8,8,4),dtype=np.float32);a[:,:,:3]=(0.1,0.8,0.1);a[:,:4,3]=0
im.pixels.foreach_set(a.reshape(-1));t.image=im;t.interpolation='Closest'
m.node_tree.links.new(t.outputs['Alpha'],m.node_tree.nodes['Principled BSDF'].inputs['Alpha'])
o.data.materials.append(m)
atlas_alpha.preserve_uv(o.data)
# Receiver atlas is flipped: coverage must follow the source UVs, not receiver UVs.
for uv in o.data.uv_layers.active.data:uv.uv.x=1-uv.uv.x
mask=atlas_alpha.bake_opacity(bpy.context.scene,o,32)
a=np.array(mask.pixels[:]).reshape(32,32,4)
print('MASK',json.dumps({'left':float(a[4:-4,4:12,0].mean()),'right':float(a[4:-4,20:28,0].mean())}))
assert a[4:-4,4:12,0].mean()>.9 and a[4:-4,20:28,0].mean()<.1
assert list(o.data.materials)==[m]
geometry = m.node_tree.nodes.new('ShaderNodeNewGeometry')
m.node_tree.links.new(geometry.outputs['Position'],m.node_tree.nodes['Principled BSDF'].inputs['Alpha'])
try:
    atlas_alpha.bake_opacity(bpy.context.scene,o,32)
    raise AssertionError('geometry-dependent alpha was accepted')
except RuntimeError as error:
    assert 'UV-based alpha' in str(error)
assert list(o.data.materials)==[m]
print('ALPHA MASK OK')
