"""Remove the detached masonry frame from an existing Registry source revision."""
import argparse,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import source_dependencies

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    frame=bpy.data.objects.get('service_hatch')
    if not frame:raise ValueError('Expected detached service hatch in the source')
    bpy.data.objects.remove(frame,do_unlink=True)
    # Move the existing joined notice board as one authored object onto the rear wall.
    notes=bpy.data.objects['registry_notices']
    wall_probe=kit.Interior.__new__(kit.Interior)
    wall_probe.parts=[bpy.data.objects['back_wall_0_pier_1']]
    rear_inside=wall_probe.bounds()[0][0]
    notes.location.x+=rear_inside-.08-1.205
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    room.wood=bpy.data.materials['registry_worked_hardwood']
    paint=bpy.data.materials['registry_worn_green_paint']
    furn.counter_returns(room,'registry_counter_returns',(.87,-.7),panel_mat=paint)
    kit.recalculate_normals(room.parts);source_dependencies.assert_available()
    bpy.context.scene['registry_plan_description']='One open room; service counter with low timber returns; no internal masonry partition'
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY OPEN PLAN REVISION OK')

if __name__=='__main__':main()
