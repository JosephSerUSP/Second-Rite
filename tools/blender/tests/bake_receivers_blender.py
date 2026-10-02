import sys,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/blender'))
import export_exterior_environment as exporter
from vendor_assets_blender import inspect_dependencies
source=ROOT/'projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
calibration_path=ROOT/'projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/camera.json'
calibration=json.loads(calibration_path.read_text(encoding='utf-8'))
assert 'projectionFrame' not in calibration
provenance=exporter.camera_provenance(calibration_path)
assert provenance['record']==calibration
assert not Path(provenance['source']).is_absolute()
inspect_dependencies()
# A missing texture is an offline failure even if the rest of the source opens.
unpacked=bpy.data.images.new('missing offline dependency',width=1,height=1)
unpacked.source='FILE';unpacked.filepath='//unpackaged/missing.png'
try:inspect_dependencies()
except ValueError as error:assert 'Unpacked' in str(error)
else:raise AssertionError('unpacked dependency accepted')
bpy.data.images.remove(unpacked)
collection=bpy.data.collections['TH_SOURCE']
role_counts={key:sum(obj.type=='MESH' and exporter.bake_role(obj)==key for obj in collection.all_objects) for key in ('both','source','receiver')}
receivers={obj.name for obj in collection.all_objects if obj.type=='MESH' and exporter.bake_role(obj)=='receiver'}
assert {'Court casement 0 glazing target','Court casement 1 glazing target','Court casement 2 glazing target','Court door leaf target'} <= receivers,receivers
assert role_counts['source']>10,role_counts
assert all(obj.hide_render for obj in collection.all_objects if obj.type=='MESH' and exporter.bake_role(obj)=='receiver')
# Silhouette-bearing main shutters and reveal geometry must survive the runtime join.
assert exporter.bake_role(bpy.data.objects['Court casement 1 left shutter target'])=='receiver'
assert exporter.bake_role(bpy.data.objects['Court casement 1 left reveal'])=='both'
assert exporter.bake_role(bpy.data.objects['Court casement 1 left louvre 0'])=='source'
beauty=exporter.bake_source_members(collection,12,6)
assert all(exporter.bake_role(obj)!='receiver' for obj in beauty)
assert any(exporter.bake_role(obj)=='source' for obj in beauty)
probe=next(iter(collection.objects));probe['sr_bake_role']='typo'
try:exporter.bake_role(probe)
except ValueError:pass
else:raise AssertionError('unknown role accepted')
probe['sr_bake_role']='both'
exporter.rebuild_render_mesh(12,6,.03,0,0,clip_ground=None,layout='legacy',atlas_size=128)
mesh=bpy.data.collections['TH_RENDER'].all_objects[0].data
assert len(mesh.polygons)>100
# Exercise visibility mutation on the actual nested assembly source through
# the production bake boundary. A live all_objects iterator crashed here.
import tempfile
import town_environment_pipeline as pipeline
import eevee_bake,atlas_allocation
settings=eevee_bake.EeveeBake(positions=[1,11.5],
    place_camera=lambda scene,y:atlas_allocation.lane_camera(scene,y,mirrored=False,record_path=calibration_path),
    sources=beauty,probe_cells=0,emissive_lights=False,fixture_lights=False,supersample=1)
with tempfile.TemporaryDirectory() as directory:
    pipeline.run_pipeline_in_blender(source,Path(directory),atlas_size=128,bake_samples=1,flat_bake=True,backend='eevee',eevee=settings)
    assert (Path(directory)/'environment.png').is_file()
print('BAKE_RECEIVER_PROOF '+json.dumps(role_counts))
