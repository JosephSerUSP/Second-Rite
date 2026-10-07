"""Round cross-sections by editing both saved meshes; no scaffold reconstruction."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
BASE=Path('docs/reports/item-model-hybrid-study/revisions/carved');SOURCE=(BASE/'source-project/assets/authoring/items').resolve()
def distance(p,a,b):
 d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return (p-a-t*d).length
for stem in ['carved_capsule_geometry','carved_capsule_baked']:
 path=SOURCE/(stem+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+stem];assert not root.get('sr_cross_section_rounding')
 if stem.endswith('geometry'):
  parts=[(bpy.data.objects['HULL_'+side],list(range(len(bpy.data.objects['HULL_'+side].data.vertices))),side) for side in ['left','right']]
 else:
  ob=bpy.data.objects['BakedAssembly'];mesh=ob.data;adj=[[] for v in mesh.vertices]
  for edge in mesh.edges:
   a,b=edge.vertices;adj[a].append(b);adj[b].append(a)
  unseen=set(range(len(mesh.vertices)));parts=[]
  while unseen:
   start=unseen.pop();group=[start];queue=[start]
   while queue:
    v=queue.pop()
    for j in adj[v]:
     if j in unseen:unseen.remove(j);group.append(j);queue.append(j)
   # Bone cheeks are the only two densely remeshed components.
   if len(group)>2000:parts.append((ob,group,'left' if sum(mesh.vertices[i].co.x for i in group)/len(group)<0 else 'right'))
  assert len(parts)==2,[len(g) for o,g,s in parts]
 for ob,indices,side in parts:
  mask=bpy.data.objects['SHADOW_HULL_'+side+'_front'];outline=[Vector((v.co.x,v.co.z)) for v in mask.data.vertices]
  lo=min(ob.data.vertices[i].co.y for i in indices);hi=max(ob.data.vertices[i].co.y for i in indices);mid=(lo+hi)/2
  for i in indices:
   v=ob.data.vertices[i];d=min(distance(Vector((v.co.x,v.co.z)),a,b) for a,b in zip(outline,outline[1:]+outline[:1]));profile=.22+.78*math.sin(min(1,d/.24)*math.pi/2)
   v.co.y=mid+(v.co.y-mid)*profile
  ob.data.update()
 root['sr_cross_section_rounding']='Saved cheek cross-sections contracted smoothly toward outline edges, 0.24-unit round-over radius, 0.22 edge depth floor.'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('SAVED CROSS SECTION EDITS')
