"""Temporary evaluated beauty batching for selected-to-active Cycles baking.

Never saves the source document. Preserve UVs, materials, world placement and
per-object Generated/Object coordinates when consolidating source meshes.
"""
import bpy
import json
import bake_correspondence

def batch_source(source):
    # One derived beauty mesh avoids per-object bake setup while preserving
    # UVs, world placement and per-object procedural coordinates.
    members=[o for o in list(source.all_objects) if o.type=='MESH' and o.get('sr_bake_role')!='receiver']
    graph=bpy.context.evaluated_depsgraph_get()
    vertices=[];faces=[];uvs=[];generated=[];local=[];materials=[];material_indices=[];smooth=[]
    face_owners=[]
    material_map={}
    default_material=None
    named_uvs={}
    for owner_index,obj in enumerate(members):
        evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
        import mesh_export_geometry
        mesh_export_geometry.prepare(mesh)
        if not mesh.vertices:
            evaluated.to_mesh_clear()
            continue
        offset=len(vertices);world=obj.matrix_world
        lows=[min(v.co[axis] for v in mesh.vertices) for axis in range(3)]
        highs=[max(v.co[axis] for v in mesh.vertices) for axis in range(3)]
        for v in mesh.vertices:
            vertices.append(tuple(world@v.co));local.append(tuple(v.co))
            generated.append(tuple((v.co[a]-lows[a])/max(highs[a]-lows[a],1e-8) for a in range(3)))
        uv=mesh.uv_layers.active
        previous_loops=len(uvs)
        for layer in mesh.uv_layers:
            if layer.name not in named_uvs:
                named_uvs[layer.name]=[(0,0)]*previous_loops
        for name, values in named_uvs.items():
            layer=mesh.uv_layers.get(name)
            values.extend(tuple(layer.data[i].uv) if layer else (0,0) for i in range(len(mesh.loops)))
        for face in mesh.polygons:
            faces.append(tuple(offset+i for i in face.vertices));smooth.append(face.use_smooth);face_owners.append(owner_index)
            uvs.extend(tuple(uv.data[i].uv) if uv else (0,0) for i in face.loop_indices)
            material=mesh.materials[face.material_index] if mesh.materials else None
            if material is None:
                if default_material is None:
                    default_material=bpy.data.materials.new('SR default source material')
                    default_material.use_nodes=True
                material=default_material
            if material.name not in material_map:
                material_map[material.name]=len(materials);materials.append(material)
            material_indices.append(material_map[material.name])
        evaluated.to_mesh_clear()
    data=bpy.data.meshes.new('SR batched beauty');data.from_pydata(vertices,[],faces);data.update()
    layer=data.uv_layers.new(name='Source UV');layer.data.foreach_set('uv',[v for uv in uvs for v in uv])
    for name,values in named_uvs.items():
        named=data.uv_layers.new(name=name)
        named.data.foreach_set('uv',[value for pair in values for value in pair])
    data.uv_layers.active=layer
    for name,values in [('sr_source_generated',generated),('sr_source_object',local)]:
        attr=data.attributes.new(name,'FLOAT_VECTOR','POINT');attr.data.foreach_set('vector',[v for row in values for v in row])
    def adapt(tree):
        attr=tree.nodes.new('ShaderNodeAttribute');attr.attribute_name='sr_source_generated'
        objattr=tree.nodes.new('ShaderNodeAttribute');objattr.attribute_name='sr_source_object'
        for node in list(tree.nodes):
            if node.type=='OBJECT_INFO' and any(output.is_linked for output in node.outputs):
                raise ValueError('Cannot batch material with Object Info dependencies; author explicit attributes: '+tree.name)
            if node.type=='TEX_COORD':
                for link in list(node.outputs['Generated'].links):tree.links.new(attr.outputs['Vector'],link.to_socket)
                if node.object is None:
                    for link in list(node.outputs['Object'].links):tree.links.new(objattr.outputs['Vector'],link.to_socket)
            elif node.type=='GROUP' and node.node_tree:
                node.node_tree=node.node_tree.copy();adapt(node.node_tree)
            elif node.type in ['TEX_NOISE','TEX_VORONOI','TEX_WAVE','TEX_GRADIENT','TEX_MAGIC','TEX_CHECKER','TEX_BRICK']:
                socket=node.inputs.get('Vector')
                if socket and not socket.is_linked:tree.links.new(attr.outputs['Vector'],socket)
    for material in materials:
        copy=material.copy()
        if copy.use_nodes:adapt(copy.node_tree)
        data.materials.append(copy)
    data.polygons.foreach_set('material_index',material_indices);data.polygons.foreach_set('use_smooth',smooth)
    owners=data.attributes.new(bake_correspondence.SOURCE_ATTRIBUTE,'INT','FACE')
    owners.data.foreach_set('value',face_owners)
    batch=bpy.data.objects.new('SR beauty batch',data);source.objects.link(batch)
    batch[bake_correspondence.SOURCE_RECORD]=json.dumps([obj.name for obj in members])
    for obj in members:
        source.objects.unlink(obj) if obj.name in source.objects else None
        bpy.data.objects.remove(obj,do_unlink=True)
    print('SOURCE BATCH',len(members),'objects to one mesh',len(vertices),'vertices',flush=True)
    return batch, len(members)
