"""Real bundled OIDN control: separate saturated charts and preserved details."""
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import atlas_denoise

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('separated charts')
mesh.from_pydata([(x,y,0) for x,y in [(0,0),(1,0),(1,1),(0,1),(2,0),(3,0),(3,1),(2,1),(4,0),(5,0),(5,1),(4,1)]],[],[(0,1,2,3),(4,5,6,7),(8,9,10,11)])
layer=mesh.uv_layers.new()
for face,rect in zip(mesh.polygons,[(.03,.03,.47,.47),(.53,.53,.97,.97),(.03,.85,.09,.91)]):
    x0,y0,x1,y1=rect
    for i,uv in zip(face.loop_indices,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]):layer.data[i].uv=uv
labels=atlas_denoise.chart_labels(mesh,64)
image=bpy.data.images.new('constant chart control',64,64,float_buffer=True)
raw=np.zeros((64,64,4),dtype=np.float32);raw[:]=[0,1,0,.37]
raw[labels==0]=[1,0,0,.61];raw[labels==1]=[0,0,1,.73];raw[labels==2]=[.7,.2,.6,.42]
image.pixels.foreach_set(raw.reshape(-1))
report=atlas_denoise.denoise(image,mesh)
after=np.array(image.pixels[:],dtype=np.float32).reshape(64,64,4)
assert report['filteredCharts']==2 and report['preservedSmallCharts']==1,report
assert np.array_equal(after[:,:,3],raw[:,:,3]),'Alpha changed'
assert np.array_equal(after[labels==2],raw[labels==2]),'Small detail changed'
assert np.array_equal(after[labels<0],raw[labels<0]),'Gutter changed'
assert np.max(after[labels==0,1:3])<.02,'Another chart contaminated red'
assert np.max(after[labels==1,:2])<.02,'Another chart contaminated blue'
print('ATLAS DENOISE ISOLATION OK',report)

# A subpixel triangle must survive rather than becoming a zero-area UV face.
tiny=bpy.data.meshes.new('texel alignment negative control')
tiny.from_pydata([(0,0,0),(1,0,0),(0,1,0),(2,0,0),(3,0,0),(2,1,0)],[],[(0,1,2),(3,4,5)])
layer=tiny.uv_layers.new()
coordinates=[(.13,.12),(.41,.12),(.13,.41),(.702,.702),(.703,.702),(.702,.703)]
for loop,coordinate in zip(layer.data,coordinates):loop.uv=coordinate
before=[tuple(v.uv) for v in layer.data]
report=atlas_denoise.snap_to_texels(tiny,64)
assert report['alignedCharts']==1 and report['preservedUnsafeCharts']==1,report
assert [tuple(v.uv) for v in layer.data][3:]==before[3:],'Tiny UV chart collapsed'
for loop in layer.data[:3]:
    for coordinate in loop.uv:assert abs((coordinate*64)-round(coordinate*64))<1e-5
print('TEXEL ALIGNMENT OK',report)

# Adjacent islands with a subpixel gutter must not acquire shared texels.
crowded=bpy.data.meshes.new('narrow gutter control')
crowded.from_pydata([(i,0,0) for i in range(8)],[],[(0,1,2,3),(4,5,6,7)])
uv=crowded.uv_layers.new().data
for face,rect in zip(crowded.polygons,[(.1,.1,.257,.4),(.259,.1,.4,.4)]):
    x0,y0,x1,y1=rect
    for i,point in zip(face.loop_indices,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]):uv[i].uv=point
report=atlas_denoise.snap_to_texels(crowded,64)
assert report['newSharedTexelPairs']==0,report
assert report['alignedCharts']==2,report
assert len(set(atlas_denoise.uv_charts(crowded)))==2,'Rounding glued unrelated charts together'
print('TEXEL GUTTER GUARD OK',report)
