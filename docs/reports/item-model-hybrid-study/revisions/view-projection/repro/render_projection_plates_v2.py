"""Read-only actual saved-geometry plates for geometry-conditioned paintovers."""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,'tools/blender');from surface_finishes import linear
BASE=Path('docs/reports/item-model-hybrid-study').resolve();OUT=BASE/'revisions/view-projection';source=BASE/'revisions/carved/source-project/assets/authoring/items/carved_capsule_geometry.blend';before=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;root=bpy.data.objects['ITEM_carved_capsule_geometry']
palette={'outer':(.78,.70,.52),'core':(.64,.31,.22),'binding':(.13,.25,.38),'spine':(.22,.14,.09),'thread':(.66,.60,.40)}
for mat in bpy.data.materials:
 role=mat.name.rsplit('_',1)[-1]
 if role in palette:mat.diffuse_color=(*linear(palette[role]),1)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.render.film_transparent=True;scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100;scene.display.shading.show_specular_highlight=False
folder=OUT/'geometry-plates-v2';folder.mkdir(exist_ok=True);views=json.loads((OUT/'projection.json').read_text())['views']
for view in views:
 name=view['name'];cam=bpy.data.objects.new('PLATE_'+name,bpy.data.cameras.new('PLATE_'+name));scene.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=4.0;cam.matrix_world=Matrix(view['cameraMatrixWorld']);scene.camera=cam
 for kind in ['material','ids']:
  scene.display.shading.light='STUDIO' if kind=='material' else 'FLAT';scene.display.shading.show_cavity=kind=='material';scene.display.shading.cavity_type='BOTH';scene.render.filepath=str(folder/(name+'-'+kind+'.png'));bpy.ops.render.render(write_still=True)
assert before==hashlib.sha256(source.read_bytes()).hexdigest();print('GEOMETRY PLATES OK; source unchanged')
