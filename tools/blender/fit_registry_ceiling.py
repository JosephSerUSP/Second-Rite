"""Fit the retained timber service divider to the existing ceiling and beams."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import source_dependencies

def signature(objects):
    return hashlib.sha256(json.dumps([(o.name,list(o.matrix_world),
        [tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],
        [m.name if m else None for m in o.data.materials]) for o in objects],default=list,sort_keys=True).encode()).hexdigest()

def bounds(obj):
    probe=kit.Interior.__new__(kit.Interior);probe.parts=[obj]
    return probe.bounds()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Use a new source revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    beams=sorted([o for o in bpy.data.objects if o.name.startswith('ceiling_beam_')],key=lambda o:o.name)
    if not beams:raise ValueError('Expected authored ceiling beams')
    shell=[bpy.data.objects['ceiling'],*beams];before=signature(shell)
    ceiling=bounds(shell[0])[0][2]
    front=.89;left=1.245;right=-2.645
    beam_bounds=[bounds(o) for o in beams]
    crossings=[(low,high) for low,high in beam_bounds if low[0]<front<high[0] and low[1]<left and high[1]>right]
    underside=min(low[2] for low,high in crossings)
    if any(abs(low[2]-underside)>.001 for low,high in crossings):
        raise ValueError('Unequal beam undersides need an individually fitted head')
    # Return crown is intentionally in the clear channel between the beams.
    if any(low[1]<left+.065 and high[1]>left-.065 for low,high in beam_bounds):
        raise ValueError('Side return intersects an authored ceiling beam')
    bpy.data.objects.remove(bpy.data.objects['wall_connected_service_screen'],do_unlink=True)
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    room.wood=bpy.data.materials['registry_worked_hardwood'];paint=bpy.data.materials['registry_worn_green_paint']
    rear=bounds(bpy.data.objects['back_wall_0_pier_1'])[0][0]
    furn.service_screen(room,'ceiling_fitted_service_screen',front=front,rear=rear,left=left,right=right,
        height=ceiling,transom_top=underside-.04,
        beam_spans=[(low[1],high[1]) for low,high in crossings],panel_mat=paint)
    # Only the new joinery needs normal preparation. Keep the authored shell byte-equivalent in mesh data.
    kit.recalculate_normals([bpy.data.objects['ceiling_fitted_service_screen']])
    assert signature(shell)==before,'Ceiling or beams changed'
    record=dict(ceilingHeight=ceiling,beamUnderside=underside,crossedBeamBands=[(low[1],high[1]) for low,high in crossings],
        shellSignature=before,existingBeamsPreserved=True)
    bpy.context.scene['registry_ceiling_fit']=json.dumps(record)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY CEILING FIT OK '+json.dumps(record))

if __name__=='__main__':main()
