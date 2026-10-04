"""Measure export geometry loss without altering the scaffold or production package."""
import argparse,collections,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/blender'))
import export_exterior_environment as exporter

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.out.exists():raise ValueError('Use a new study directory')
    args.out.mkdir(parents=True)
    before=hashlib.sha256(args.source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    original=exporter.realised_mesh
    owners={};names={};roof_normals={}
    for obj in list(bpy.data.collections['TH_SOURCE'].all_objects):
        if obj.type=='MESH' and (obj.name.endswith(' roof') or obj.name.endswith('gable')):
            obj.data.calc_loop_triangles()
            roof_normals[obj.name]={'faceNormals':[list(face.normal) for face in obj.data.polygons],
                'signedVolume':sum(obj.data.vertices[t.vertices[0]].co.dot(obj.data.vertices[t.vertices[1]].co.cross(obj.data.vertices[t.vertices[2]].co))/6 for t in obj.data.loop_triangles)}
    def tagged(obj):
        mesh=original(obj)
        index=owners.setdefault(obj.name,len(owners)+1);names[index]=obj.name
        tag=mesh.attributes.new('study_source_owner','INT','FACE')
        tag.data.foreach_set('value',[index]*len(mesh.polygons))
        return mesh
    exporter.realised_mesh=tagged
    def count():
        mesh=bpy.data.collections['TH_RENDER'].all_objects[0].data
        mesh.calc_loop_triangles()
        tags=mesh.attributes['study_source_owner'].data
        rows=collections.Counter(names[tags[t.polygon_index].value] for t in mesh.loop_triangles)
        return {'totalTriangles':len(mesh.loop_triangles),'objects':dict(rows)}
    exporter.rebuild_render_mesh(12,6,.03,0,0,clip_ground=None,layout='legacy',atlas_size=128)
    unculled=count()
    exporter.rebuild_render_mesh(12,6,.03,24,0,clip_ground=None,layout='legacy',atlas_size=128)
    culled=count()
    import bmesh
    for obj in bpy.data.collections['TH_SOURCE'].all_objects:
        if obj.type=='MESH' and obj.name.endswith(' roof'):
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            bm.to_mesh(obj.data);bm.free();obj.data.update()
    exporter.rebuild_render_mesh(12,6,.03,24,0,clip_ground=None,layout='legacy',atlas_size=128)
    repaired=count()
    result={'sourceSHA256':before,'unculled':unculled,'culled':culled,'repairedRoofNormals':repaired,'roofNormals':roof_normals,
        'roofTriangles':{name:{'before':unculled['objects'].get(name,0),'after':culled['objects'].get(name,0),'afterNormalRepair':repaired['objects'].get(name,0)} for name in roof_normals},
        'interpretation':'Controlled culling A/B with identical admitted proxy objects; ground clipping disabled and legacy atlas layout to isolate geometry deletion.'}
    (args.out/'measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==before
    print('GEOMETRY LOSS STUDY OK',json.dumps(result['roofTriangles']),flush=True)
if __name__=='__main__':main()
