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
assert {'Window receiver 0.5','Window receiver 3.5','Window receiver 6.8','Lodging door receiver'} <= receivers,receivers
assert role_counts['source']>10,role_counts
assert all(obj.hide_render for obj in collection.all_objects if obj.type=='MESH' and exporter.bake_role(obj)=='receiver')
# Silhouette-bearing main shutters and reveal geometry must survive the runtime join.
assert exporter.bake_role(bpy.data.objects['lodging_window_1_shutter_l'])=='both'
assert exporter.bake_role(bpy.data.objects['lodging_window_1_jamb_l'])=='both'
assert exporter.bake_role(bpy.data.objects['lodging_window_1_shutter_l_panel_0'])=='source'
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
print('BAKE_RECEIVER_PROOF '+json.dumps(role_counts))
