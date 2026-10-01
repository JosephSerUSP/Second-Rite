"""Map-owned paving and repository-local material adaptations."""
import math
import bpy

def mesh(name,vertices,faces,collection,material=None,bake=True):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    if material:data.materials.append(material)
    obj['sr_bake_source']=bake
    return obj

def profile_surface(name,profile,near_x,far_x,collection,material=None,bake=True,depth_step=None):
    # The authored control points create planar segments; this does not define
    # another gameplay elevation evaluator.
    count=max(1,math.ceil((far_x-near_x)/depth_step)) if depth_step else 1
    xs=[near_x+(far_x-near_x)*i/count for i in range(count+1)]
    vertices=[(x,point['y'],point['z']) for point in profile for x in xs]
    faces=[(i*(count+1)+j,i*(count+1)+j+1,(i+1)*(count+1)+j+1,(i+1)*(count+1)+j) for i in range(len(profile)-1) for j in range(count)]
    return mesh(name,vertices,faces,collection,material,bake)

def adapted_material(source,name,color,**inputs):
    material=source.copy();material.name=name;material.asset_clear()
    group=next(node for node in material.node_tree.nodes if node.type=='GROUP')
    group.inputs['Base Color'].default_value=(*color,1)
    for key,value in inputs.items():group.inputs[key].default_value=value
    material['upstream_asset']=source.name;material['project_adaptation']=True
    return material
