"""Edit the retained Registry: larger records press and a public-side woven runner."""
import argparse,json,math,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import surface_finishes
import source_dependencies
from fit_registry_ceiling import bounds,signature

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Use a new source revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    shell=[bpy.data.objects['ceiling'],*[o for o in bpy.data.objects if o.name.startswith('ceiling_beam_')]]
    before=signature(shell);wall=bounds(bpy.data.objects['side_wall_0_pier_0'])[1][1]
    bpy.data.objects.remove(bpy.data.objects['right_wall_records_cabinet'],do_unlink=True)
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.parts=[o for o in bpy.data.objects if o.type=='MESH'];start=len(room.parts)
    room.wood=bpy.data.materials['registry_worked_hardwood'];room.iron=bpy.data.materials['sr_wrought_iron']
    room.bronze=bpy.data.materials['sr_oxidized_bronze'];room.paper=bpy.data.materials['registry_rag_paper']
    panels=surface_finishes.finish('registry_dark_cupboard_panels',kit.material('dark_wood'),
        colours=((.12,.065,.027),(.29,.16,.065)),grain=(5,35,6),scale=2,relief=.002,roughness=.64)
    furn.records_press(room,'right_wall_records_press',(0,0),panel_mat=panels)
    cabinet=bpy.data.objects['right_wall_records_press'];cabinet.rotation_euler.z=-math.pi/2
    cabinet.location.x=3.32;cabinet.location.y=wall+.41
    bpy.context.view_layer.update();cabinet.location.y+=wall-bounds(cabinet)[0][1]
    cloth=surface_finishes.finish('registry_rust_woven_rug',kit.material('aged_cloth'),
        colours=((.27,.075,.045),(.50,.22,.095)),grain=(30,1,30),scale=4,relief=.0008,roughness=.97)
    border=surface_finishes.finish('registry_ochre_rug_border',kit.material('aged_cloth'),
        colours=((.40,.25,.09),(.63,.45,.20)),scale=6,relief=.0008,roughness=.97)
    motif=surface_finishes.finish('registry_cream_rug_thread',kit.material('aged_cloth'),
        colours=((.57,.47,.29),(.77,.65,.43)),scale=6,relief=.0008,roughness=.97)
    furn.woven_runner(room,'public_waiting_runner',(-.95,-1.25),cloth_mat=cloth,border_mat=border,motif_mat=motif)
    kit.recalculate_normals(room.parts[start:]);bpy.context.view_layer.update()
    assert abs(bounds(cabinet)[0][1]-wall)<1e-5,'Cupboard trim is not seated at the wall'
    assert signature(shell)==before,'Existing ceiling or beams changed'
    bpy.context.scene['registry_cabinet_rug_revision']=json.dumps(dict(cupboardNominalSize=[2.1,.82,2.8],
        rugNominalSize=[4.7,1.55],decorativeOnly=True,existingCeilingAndBeamsPreserved=True))
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY CUPBOARD AND RUNNER OK')

if __name__=='__main__':main()
