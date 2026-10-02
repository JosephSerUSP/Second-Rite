"""Edit an existing Registry document into the recessed service-hatch study."""
import argparse
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/blender/recipes'))
sys.path.insert(0, str(ROOT/'tools/blender'))
import interior as kit
import furnishings as furn
import source_dependencies

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.output.exists(): parser.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()
    for name in ('registrar_desk','current_ledger','previous_ledger','registration_seal',
                 'registrar_chair','archive_cabinet','visitor_bench','water_jar'):
        obj=bpy.data.objects.get(name)
        if obj: bpy.data.objects.remove(obj,do_unlink=True)
    room=kit.Interior.__new__(kit.Interior)
    room.root=bpy.data.objects['PASSAGE_OFFICE']; room.lift=0
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    for attr,key in [('wood','dark_wood'),('iron','wrought_iron'),('bronze','oxidized_bronze'),
                     ('whitewash','whitewash'),('paper','paper'),('leather','book_leather'),('ink','writing_ink')]:
        setattr(room,attr,kit.material(key))
    furn.service_counter(room,'registry_counter',(.45,-.7))
    with room.piece('service_hatch'):
        for y in (-3.05,1.65):
            room.part('hatch_pier',(.8,.7,3.65),(1.65,y,1.825),room.whitewash)
            room.part('hatch_jamb',(.14,.12,2.12),(1.18,y+(.4 if y<0 else -.4),2.06),room.wood)
        room.part('hatch_lintel',(.8,4.7,.62),(1.65,-.7,3.34),room.whitewash)
        room.part('hatch_header',(.18,4.1,.16),(1.18,-.7,3.0),room.wood)
    furn.record_bay(room,'record_pigeonholes',(3.7,-.7),width=2.8,height=2.35,columns=5,rows=4)
    furn.waiting_bench(room,'waiting_bench',(2.7,3.15),length=1.6)
    with room.surface(1.007):
        furn.ledger(room,'current_ledger',(.42,-.9),open_book=True)
        furn.ledger(room,'previous_ledger',(.5,-.2))
        furn.seal_stamp(room,'registration_seal',(.35,-1.5))
    kit.recalculate_normals(room.parts)
    bpy.context.scene['registry_npc_x']=1.15
    bpy.context.scene['registry_npc_y']=4.5833
    bpy.ops.file.pack_all()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('REGISTRY REVISION SAVED')

if __name__=='__main__': main()
