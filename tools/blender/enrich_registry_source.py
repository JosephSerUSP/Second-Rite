"""Edit the Registry document: tactile finishes, coherent windows, selected props."""
import argparse,sys,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import opening_families
import surface_finishes
import source_dependencies

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--painting',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Use a new source revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.asset_id='passage_office';room.record=kit.camera_record()
    room.half_width=4.65;room.depth=6.8;room.ceiling_z=3.65
    room.front_x=kit.floor_edge_x(136,room.record)[0];room.back_x=room.front_x+room.depth
    room.wall_thick=.5;room.floor_thick=.35;room.ceiling_thick=.3
    room.daylight=kit.emissive('registry_daylight',(0.92,.95,1))
    room.wood=surface_finishes.finish('registry_worked_hardwood',kit.material('dark_wood'),
        colours=((.20,.10,.04),(.47,.28,.12)),scale=2,grain=(5,35,6),relief=.002,roughness=.56)
    room.whitewash=surface_finishes.finish('registry_brushed_limewash',kit.material('whitewash'),
        colours=((.63,.57,.43),(.91,.86,.72)),scale=2.6,grain=(1,1,1.5),relief=.007,roughness=.95)
    paint=surface_finishes.finish('registry_worn_green_paint',kit.material('dark_wood'),
        colours=((.12,.25,.19),(.37,.46,.28)),scale=2.5,grain=(3,6,2),relief=.002,roughness=.66,wear=(.40,.22,.085))
    room.panel=paint;room.iron=kit.material('wrought_iron');room.stone=kit.material('old_limestone')
    room.terracotta=surface_finishes.finish('registry_unglazed_clay',kit.material('terracotta'),
        colours=((.29,.10,.045),(.62,.29,.13)),scale=4,relief=.004,roughness=.92)
    room.paper=bpy.data.materials['registry_rag_paper'];room.ink=bpy.data.materials['registry_stamp_ink']
    room.glass=kit.material('smoked_glass').copy();room.glass.name='registry_clear_casement_glass'
    shader=next(n for n in room.glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value=(.84,.90,.86,1);shader.inputs['Transmission Weight'].default_value=1
    shader.inputs['Roughness'].default_value=.12;shader.inputs['IOR'].default_value=1.45
    for obj in list(bpy.data.objects):
        if obj.name.startswith('side_wall_1_') or obj.name in ('writing_window','window_sill'):
            bpy.data.objects.remove(obj,do_unlink=True);continue
        if obj.type!='MESH':continue
        for i,mat in enumerate(obj.data.materials):
            if not mat:continue
            if mat.get('sr_material_id')=='whitewash':obj.data.materials[i]=room.whitewash
            elif mat.name=='registry_counter_paint':obj.data.materials[i]=paint
            elif mat.get('sr_material_id')=='dark_wood':obj.data.materials[i]=room.wood
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    # Screen-left wall is +Y. Rebuild only that wall around its real aperture.
    window=(1.20,3.65,1.35,2.95)
    room._pierced_run('side_wall_1',room.front_x,room.back_x,4.9,.5,[window],room.whitewash,axis='x')
    room.side_window(1,*window)
    room.side_window_light(1,2.425,2.15,energy=520)
    with room.piece('left_window_assembly'):
        opening_families.two_sided_window(room,'registry_left_window',(2.425,4.65,2.15),(0,1,0),width=2.45,height=1.6)
    with room.piece('rear_window_assembly'):
        opening_families.two_sided_window(room,'registry_rear_window',(room.back_x,-2.65,2.175),(1,0,0),width=1.9,height=1.55)
    # One painting over the waiting bench; image is a local, packed project asset.
    art=bpy.data.materials.new('registry_harbour_painting');art.use_nodes=True;art['sr_material_id']='aged_cloth'
    bsdf=next(n for n in art.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    image=bpy.data.images.load(str(a.painting.resolve()));tex=art.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    art.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);bsdf.inputs['Roughness'].default_value=.90
    furn.framed_picture(room,'harbour_painting',(room.back_x-.08,3.35,2.25),width=1.25,height=.94,artwork=art)
    with room.piece('registry_notices'):
        room.part('notices_board',(.065,.59,.78),(1.205,1.65,1.95),room.wood)
        for i,(dy,dz) in enumerate(((-.13,.13),(.12,.08),(-.08,-.19))):
            room.part('pinned_writ',(.007,.19,.24),(1.165,1.65+dy,1.95+dz),room.paper)
            for line in range(3):
                room.part('ink_rule',(.003,.12-.018*line,.008),(1.158,1.65+dy,1.99+dz-line*.032),room.ink)
            room.part('notice_pin',(.012,.014,.014),(1.155,1.65+dy,2.05+dz),room.iron)
    # Near-left grouping catches the window light; action lane and exit remain clear.
    furn.table(room,'foreground_plant_table',(-1.05,3.95),length=.64,width=.66,height=.68)
    leaves=surface_finishes.finish('registry_plant_leaves',kit.material('foliage'),
        colours=((.085,.16,.045),(.31,.40,.10)),scale=6,relief=.001,roughness=.6)
    with room.surface(.72):
        furn.potted_plant(room,'foreground_plant',(-1.05,3.95),foliage_mat=leaves)
    kit.recalculate_normals(room.parts);bpy.ops.file.pack_all()
    bpy.context.scene['registry_window_convention']='External shutters outward; inner glazed casements inward; fixed exterior iron grille'
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY MATERIAL / WINDOW / COMPOSITION REVISION OK')

if __name__=='__main__':main()
